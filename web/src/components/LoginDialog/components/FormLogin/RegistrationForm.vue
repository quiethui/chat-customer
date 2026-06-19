<!-- 注册表单 -->
<script lang="ts" setup>
import type { FormInstance, FormRules } from 'element-plus';
import type { RegisterDTO } from '@/api/auth/types';
import { reactive, ref } from 'vue';
import { register } from '@/api';
import { useLoginFormStore } from '@/stores/modules/loginForm';

const loginFromStore = useLoginFormStore();
const formRef = ref<FormInstance>();

const formModel = ref<RegisterDTO>({
  username: '',
  password: '',
  confirmPassword: '',
});

const rules = reactive<FormRules<RegisterDTO>>({
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  confirmPassword: [
    { required: true, message: '请输入确认密码', trigger: 'blur' },
    {
      validator: (_, value) => {
        if (value !== formModel.value.password) {
          return new Error('两次输入的密码不一致');
        }
        return true;
      },
      trigger: 'change',
    },
  ],
});

async function handleSubmit() {
  try {
    await formRef.value?.validate();
    await register({
      username: formModel.value.username,
      password: formModel.value.password,
      confirmPassword: formModel.value.confirmPassword,
    });
    ElMessage.success('注册成功，请登录');
    formRef.value?.resetFields();
    loginFromStore.setLoginFormType('AccountPassword');
  }
  catch (error) {
    console.error('请求错误:', error);
  }
}
</script>

<template>
  <div class="custom-form">
    <el-form
      ref="formRef"
      :model="formModel"
      :rules="rules"
      style="width: 230px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item prop="username">
        <el-input v-model="formModel.username" placeholder="请输入用户名" autocomplete="off">
          <template #prefix>
            <el-icon>
              <User />
            </el-icon>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item prop="password">
        <el-input v-model="formModel.password" placeholder="请输入密码" type="password" show-password autocomplete="off">
          <template #prefix>
            <el-icon>
              <Unlock />
            </el-icon>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item prop="confirmPassword">
        <el-input v-model="formModel.confirmPassword" placeholder="请确认密码" type="password" show-password autocomplete="off">
          <template #prefix>
            <el-icon>
              <Lock />
            </el-icon>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" style="width: 100%" native-type="submit">
          注册
        </el-button>
      </el-form-item>
    </el-form>

    <div class="form-tip font-size-12px flex items-center">
      <span>已有账号，</span>
      <span
        class="c-[var(--el-color-primar,#409eff)] cursor-pointer"
        @click="loginFromStore.setLoginFormType('AccountPassword')"
      >
        返回登录
      </span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.custom-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.form-group {
  display: flex;
  gap: 8px;
  align-items: center;
}
.login-btn {
  padding: 12px;
  margin-top: 24px;
  color: white;
  cursor: pointer;
  background: #409eff;
  border: none;
  border-radius: 4px;
}
</style>
