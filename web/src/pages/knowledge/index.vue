<script setup lang="ts">
import type { FormInstance, FormRules } from 'element-plus';
import type { KnowledgeBaseItem, KnowledgeChunkItem, KnowledgeFileItem } from '@/api/knowledge';
import {
  createKnowledgeBase,
  deleteKnowledgeBaseFile,
  getKnowledgeBaseFiles,
  getKnowledgeBases,
  getKnowledgeFileChunks,
  reembeddingKnowledgeBaseFile,
  reparseKnowledgeBaseFile,
  reuploadKnowledgeBaseFile,
  uploadKnowledgeBaseFile,
} from '@/api/knowledge';

interface KnowledgeBaseForm {
  name: string;
  description: string;
}

const loadingBases = ref(false);
const loadingFiles = ref(false);
const uploading = ref(false);
const reuploadingFileId = ref<number | null>(null);
const reparsingFileId = ref<number | null>(null);
const reembeddingFileId = ref<number | null>(null);
const chunkDrawerVisible = ref(false);
const loadingChunks = ref(false);
const createDialogVisible = ref(false);
const knowledgeBases = ref<KnowledgeBaseItem[]>([]);
const knowledgeFiles = ref<KnowledgeFileItem[]>([]);
const chunkList = ref<KnowledgeChunkItem[]>([]);
const currentChunkFile = ref<KnowledgeFileItem | null>(null);
const activeBaseId = ref<number | null>(null);
const uploadInputRef = ref<HTMLInputElement | null>(null);
const reuploadInputRef = ref<HTMLInputElement | null>(null);
const pendingReuploadFileId = ref<number | null>(null);
const formRef = ref<FormInstance | null>(null);
const form = reactive<KnowledgeBaseForm>({
  name: '',
  description: '',
});

const formRules: FormRules<KnowledgeBaseForm> = {
  name: [
    { required: true, message: '请输入知识库名称', trigger: 'blur' },
    { min: 1, max: 100, message: '名称长度不能超过 100 个字符', trigger: 'blur' },
  ],
  description: [{ max: 500, message: '描述长度不能超过 500 个字符', trigger: 'blur' }],
};

const activeBase = computed(() => knowledgeBases.value.find(item => item.id === activeBaseId.value) || null);
const totalChunks = computed(() => knowledgeFiles.value.reduce((total, item) => total + item.chunk_count, 0));
const hasProcessingFiles = computed(() => knowledgeFiles.value.some(item => item.status === 'processing'));
let processingRefreshTimer: number | null = null;

function clearProcessingRefreshTimer() {
  if (processingRefreshTimer) {
    window.clearTimeout(processingRefreshTimer);
    processingRefreshTimer = null;
  }
}

function scheduleProcessingRefresh() {
  clearProcessingRefreshTimer();
  if (!hasProcessingFiles.value || !activeBaseId.value)
    return;
  processingRefreshTimer = window.setTimeout(() => {
    processingRefreshTimer = null;
    if (activeBaseId.value) {
      requestKnowledgeFiles(activeBaseId.value);
    }
  }, 3000);
}

onUnmounted(() => {
  clearProcessingRefreshTimer();
});

onMounted(async () => {
  await requestKnowledgeBases();
});

async function requestKnowledgeBases() {
  loadingBases.value = true;
  try {
    const res = await getKnowledgeBases();
    knowledgeBases.value = res.data;
    if (!activeBaseId.value && knowledgeBases.value.length) {
      activeBaseId.value = knowledgeBases.value[0].id;
    }
    if (activeBaseId.value) {
      await requestKnowledgeFiles(activeBaseId.value);
    }
  }
  catch (err) {
    showError(err, '知识库列表加载失败');
  }
  finally {
    loadingBases.value = false;
  }
}

async function requestKnowledgeFiles(knowledgeBaseId: number) {
  loadingFiles.value = true;
  try {
    const res = await getKnowledgeBaseFiles(knowledgeBaseId);
    knowledgeFiles.value = res.data;
  }
  catch (err) {
    knowledgeFiles.value = [];
    showError(err, '文件列表加载失败');
  }
  finally {
    loadingFiles.value = false;
    scheduleProcessingRefresh();
  }
}

async function handleBaseChange(knowledgeBaseId: number) {
  activeBaseId.value = knowledgeBaseId;
  await requestKnowledgeFiles(knowledgeBaseId);
}

function openCreateDialog() {
  form.name = '';
  form.description = '';
  createDialogVisible.value = true;
  nextTick(() => formRef.value?.clearValidate());
}

async function submitCreateBase() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid)
    return;

  try {
    const res = await createKnowledgeBase({
      name: form.name.trim(),
      description: form.description.trim() || undefined,
    });
    ElMessage.success('知识库创建成功');
    createDialogVisible.value = false;
    activeBaseId.value = res.data.id;
    await requestKnowledgeBases();
  }
  catch (err) {
    showError(err, '知识库创建失败');
  }
}

function triggerUpload() {
  if (!activeBaseId.value) {
    ElMessage.warning('请先选择知识库');
    return;
  }
  uploadInputRef.value?.click();
}

async function handleUploadChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file || !activeBaseId.value)
    return;

  uploading.value = true;
  try {
    await uploadKnowledgeBaseFile(activeBaseId.value, file);
    ElMessage.success('上传成功，文件正在后台处理中');
    await requestKnowledgeFiles(activeBaseId.value);
  }
  catch (err) {
    showError(err, '文件上传失败');
  }
  finally {
    uploading.value = false;
  }
}

function triggerReupload(fileId: number) {
  pendingReuploadFileId.value = fileId;
  reuploadInputRef.value?.click();
}

async function handleReuploadChange(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file || !activeBaseId.value || !pendingReuploadFileId.value)
    return;

  reuploadingFileId.value = pendingReuploadFileId.value;
  try {
    await reuploadKnowledgeBaseFile(activeBaseId.value, pendingReuploadFileId.value, file);
    ElMessage.success('重新上传成功，文件正在后台处理中');
    await requestKnowledgeFiles(activeBaseId.value);
  }
  catch (err) {
    showError(err, '重新上传失败');
  }
  finally {
    reuploadingFileId.value = null;
    pendingReuploadFileId.value = null;
  }
}

async function handleDeleteFile(row: KnowledgeFileItem) {
  if (!activeBaseId.value)
    return;

  try {
    await ElMessageBox.confirm(
      `确定删除文件「${row.filename}」吗？删除后会同步删除 MySQL 切块和向量库向量。`,
      '删除文件',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger',
      },
    );
    await deleteKnowledgeBaseFile(activeBaseId.value, row.id);
    ElMessage.success('文件删除成功');
    await requestKnowledgeFiles(activeBaseId.value);
  }
  catch (err: any) {
    if (err === 'cancel' || err === 'close')
      return;
    showError(err, '文件删除失败');
  }
}

async function openChunkDrawer(row: KnowledgeFileItem) {
  currentChunkFile.value = row;
  chunkDrawerVisible.value = true;
  await requestChunks(row);
}

async function requestChunks(row = currentChunkFile.value) {
  if (!activeBaseId.value || !row)
    return;
  loadingChunks.value = true;
  try {
    const res = await getKnowledgeFileChunks(activeBaseId.value, row.id);
    chunkList.value = res.data;
  }
  catch (err) {
    chunkList.value = [];
    showError(err, 'Chunk 加载失败');
  }
  finally {
    loadingChunks.value = false;
  }
}

async function handleReparseFile(row: KnowledgeFileItem) {
  if (!activeBaseId.value)
    return;
  try {
    await ElMessageBox.confirm(
      `确定重新解析文件「${row.filename}」吗？系统会按原始文件重新切块，并重建向量。`,
      '重新解析',
      {
        confirmButtonText: '确定执行',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
    reparsingFileId.value = row.id;
    const res = await reparseKnowledgeBaseFile(activeBaseId.value, row.id);
    ElMessage.success(`重新解析成功，写入 ${res.data.chunk_count} 个切块`);
    await requestKnowledgeFiles(activeBaseId.value);
    if (currentChunkFile.value?.id === row.id) {
      await requestChunks(row);
    }
  }
  catch (err: any) {
    if (err === 'cancel' || err === 'close')
      return;
    showError(err, '重新解析失败');
  }
  finally {
    reparsingFileId.value = null;
  }
}

async function handleReembeddingFile(row: KnowledgeFileItem) {
  if (!activeBaseId.value)
    return;
  try {
    await ElMessageBox.confirm(
      `确定重新 embedding 文件「${row.filename}」吗？系统会保留现有 Chunk 文本，仅重新生成并替换向量。`,
      '重新 embedding',
      {
        confirmButtonText: '确定执行',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );
    reembeddingFileId.value = row.id;
    const res = await reembeddingKnowledgeBaseFile(activeBaseId.value, row.id);
    ElMessage.success(`重新 embedding 成功，处理 ${res.data.chunk_count} 个切块`);
    await requestKnowledgeFiles(activeBaseId.value);
    if (currentChunkFile.value?.id === row.id) {
      await requestChunks(row);
    }
  }
  catch (err: any) {
    if (err === 'cancel' || err === 'close')
      return;
    showError(err, '重新 embedding 失败');
  }
  finally {
    reembeddingFileId.value = null;
  }
}

function formatTime(value: string) {
  if (!value)
    return '-';
  return value.replace('T', ' ').slice(0, 19);
}

function statusText(status: string) {
  const map: Record<string, string> = {
    processing: '处理中',
    active: '可用',
    deleted: '已删除',
    failed: '处理失败',
  };
  return map[status] || status;
}

function statusType(status: string) {
  if (status === 'active')
    return 'success';
  if (status === 'processing')
    return 'warning';
  if (status === 'failed')
    return 'danger';
  return 'info';
}

function showError(err: any, fallback: string) {
  ElMessage.error(err?.message || fallback);
}
</script>

<template>
  <div class="knowledge-page">
    <div class="page-header">
      <div>
        <div class="page-title">知识库管理</div>
        <div class="page-subtitle">管理多个知识库的文件、切块和向量</div>
      </div>
      <div class="header-actions">
        <el-button @click="requestKnowledgeBases">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          新建知识库
        </el-button>
      </div>
    </div>

    <div class="content-layout">
      <el-card class="base-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span>知识库列表</span>
            <el-tag size="small" effect="plain">{{ knowledgeBases.length }} 个</el-tag>
          </div>
        </template>

        <el-skeleton v-if="loadingBases" :rows="5" animated />
        <el-empty v-else-if="!knowledgeBases.length" description="暂无知识库">
          <el-button type="primary" @click="openCreateDialog">创建知识库</el-button>
        </el-empty>
        <div v-else class="base-list">
          <button
            v-for="item in knowledgeBases"
            :key="item.id"
            class="base-item"
            :class="{ active: item.id === activeBaseId }"
            @click="handleBaseChange(item.id)"
          >
            <div class="base-name">{{ item.name }}</div>
            <div class="base-desc">{{ item.description || '暂无描述' }}</div>
            <div class="base-time">创建于 {{ formatTime(item.created_at) }}</div>
          </button>
        </div>
      </el-card>

      <div class="file-panel">
        <el-card class="summary-card" shadow="never">
          <div class="summary-content">
            <div>
              <div class="summary-title">{{ activeBase?.name || '请选择知识库' }}</div>
              <div class="summary-desc">{{ activeBase?.description || '选择左侧知识库后，可上传、删除或重新上传文件。' }}</div>
            </div>
            <div class="summary-stats">
              <div class="stat-item">
                <span class="stat-value">{{ knowledgeFiles.length }}</span>
                <span class="stat-label">文件数</span>
              </div>
              <div class="stat-item">
                <span class="stat-value">{{ totalChunks }}</span>
                <span class="stat-label">切块数</span>
              </div>
            </div>
          </div>
        </el-card>

        <el-card class="table-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>文件列表</span>
              <div class="table-actions">
                <el-button :disabled="!activeBaseId" :loading="loadingFiles" @click="activeBaseId && requestKnowledgeFiles(activeBaseId)">
                  刷新文件
                </el-button>
                <el-button type="primary" :disabled="!activeBaseId" :loading="uploading" @click="triggerUpload">
                  <el-icon><Upload /></el-icon>
                  上传文件
                </el-button>
              </div>
            </div>
          </template>

          <input ref="uploadInputRef" type="file" class="hidden-input" accept=".txt,.md,.pdf,.docx" @change="handleUploadChange">
          <input ref="reuploadInputRef" type="file" class="hidden-input" accept=".txt,.md,.pdf,.docx" @change="handleReuploadChange">

          <el-alert
            class="mb-16px"
            title="支持 txt、md、pdf、docx。上传后会先进入处理中状态，后台完成解析、切块、生成 embedding 和写入向量库。"
            type="info"
            show-icon
            :closable="false"
          />

          <el-table v-loading="loadingFiles" :data="knowledgeFiles" height="calc(100vh - 360px)" empty-text="暂无文件">
            <el-table-column prop="filename" label="文件名" min-width="220" show-overflow-tooltip />
            <el-table-column prop="chunk_count" label="切块数" width="100" align="center" />
            <el-table-column prop="status" label="状态" width="110">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" effect="plain">{{ statusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="上传时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="file_path" label="保存路径" min-width="260" show-overflow-tooltip />
            <el-table-column label="操作" width="360" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" :disabled="row.status === 'processing'" @click="openChunkDrawer(row)">
                  查看 Chunk
                </el-button>
                <el-button link type="primary" :disabled="row.status === 'processing'" :loading="reuploadingFileId === row.id" @click="triggerReupload(row.id)">
                  重新上传
                </el-button>
                <el-button link type="warning" :disabled="row.status === 'processing'" :loading="reparsingFileId === row.id" @click="handleReparseFile(row)">
                  重新解析
                </el-button>
                <el-button link type="success" :disabled="row.status === 'processing'" :loading="reembeddingFileId === row.id" @click="handleReembeddingFile(row)">
                  重新 embedding
                </el-button>
                <el-button link type="danger" @click="handleDeleteFile(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </div>

    <el-dialog v-model="createDialogVisible" title="新建知识库" width="520px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="96px">
        <el-form-item label="知识库名称" prop="name">
          <el-input v-model="form.name" maxlength="100" show-word-limit placeholder="例如：订单知识库" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            maxlength="500"
            show-word-limit
            :rows="4"
            placeholder="说明该知识库的业务范围"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitCreateBase">确定创建</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="chunkDrawerVisible" size="72%" direction="rtl" destroy-on-close>
      <template #header>
        <div class="chunk-drawer-header">
          <div>
            <div class="chunk-drawer-title">Chunk 列表</div>
            <div class="chunk-drawer-subtitle">{{ currentChunkFile?.filename || '-' }}</div>
          </div>
          <el-button :loading="loadingChunks" @click="requestChunks()">刷新</el-button>
        </div>
      </template>

      <el-alert
        class="mb-16px"
        title="重新解析会按原始文件重新切块并重建向量；重新 embedding 会保留现有 Chunk 文本，仅重新生成向量。"
        type="info"
        show-icon
        :closable="false"
      />

      <el-table v-loading="loadingChunks" :data="chunkList" height="calc(100vh - 190px)" empty-text="暂无 Chunk">
        <el-table-column prop="chunk_index" label="#" width="72" align="center" />
        <el-table-column prop="content" label="Chunk 内容" min-width="420">
          <template #default="{ row }">
            <div class="chunk-content">{{ row.content }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="char_count" label="字符数" width="90" align="center" />
        <el-table-column prop="vector_id" label="Vector ID" width="260" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<style scoped lang="scss">
.knowledge-page {
  box-sizing: border-box;
  height: 100vh;
  padding: 24px;
  overflow-x: hidden;
  overflow-y: auto;
  background: #f5f7fb;
  -webkit-overflow-scrolling: touch;

  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 20px 24px;
    margin-bottom: 20px;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
  }

  .page-title {
    font-size: 24px;
    font-weight: 700;
    color: #111827;
  }

  .page-subtitle {
    margin-top: 6px;
    font-size: 14px;
    color: #6b7280;
  }

  .header-actions,
  .table-actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .content-layout {
    display: grid;
    grid-template-columns: 320px minmax(0, 1fr);
    gap: 20px;
  }

  .base-card,
  .summary-card,
  .table-card {
    border: 1px solid #e5e7eb;
    border-radius: 18px;
  }

  .base-card {
    height: calc(100vh - 112px);
    overflow: hidden;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 700;
  }

  .base-list {
    display: flex;
    flex-direction: column;
    gap: 10px;
    max-height: calc(100vh - 210px);
    overflow-y: auto;
  }

  .base-item {
    width: 100%;
    padding: 14px;
    text-align: left;
    cursor: pointer;
    background: #f9fafb;
    border: 1px solid transparent;
    border-radius: 14px;
    transition: all 0.2s ease;

    &:hover,
    &.active {
      background: #eef5ff;
      border-color: #93c5fd;
    }
  }

  .base-name {
    font-size: 15px;
    font-weight: 700;
    color: #111827;
  }

  .base-desc,
  .base-time {
    margin-top: 6px;
    font-size: 12px;
    line-height: 18px;
    color: #6b7280;
  }

  .file-panel {
    display: flex;
    flex-direction: column;
    gap: 20px;
    min-width: 0;
  }

  .summary-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
  }

  .summary-title {
    font-size: 20px;
    font-weight: 700;
    color: #111827;
  }

  .summary-desc {
    margin-top: 8px;
    color: #6b7280;
  }

  .summary-stats {
    display: flex;
    gap: 12px;
  }

  .stat-item {
    min-width: 92px;
    padding: 12px 16px;
    text-align: center;
    background: #f9fafb;
    border-radius: 14px;
  }

  .stat-value {
    display: block;
    font-size: 22px;
    font-weight: 700;
    color: #2563eb;
  }

  .stat-label {
    display: block;
    margin-top: 4px;
    font-size: 12px;
    color: #6b7280;
  }

  .hidden-input {
    display: none;
  }

  .chunk-drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }

  .chunk-drawer-title {
    font-size: 18px;
    font-weight: 700;
    color: #111827;
  }

  .chunk-drawer-subtitle {
    margin-top: 4px;
    font-size: 13px;
    color: #6b7280;
  }

  .chunk-content {
    max-height: 160px;
    overflow: auto;
    line-height: 1.7;
    white-space: pre-wrap;
  }

  .mb-16px {
    margin-bottom: 16px;
  }
}

@media (max-width: 960px) {
  .knowledge-page {
    padding: 16px;

    .page-header,
    .summary-content {
      align-items: flex-start;
      flex-direction: column;
    }

    .content-layout {
      grid-template-columns: 1fr;
    }

    .base-card {
      height: auto;
    }

    .base-list {
      max-height: 320px;
    }

    :deep(.el-table) {
      min-width: 760px;
    }

    :deep(.el-card__body) {
      overflow-x: auto;
    }
  }
}
</style>
