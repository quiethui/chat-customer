import type { NavigationGuardNext, RouteLocationNormalized } from 'vue-router';
import { useNProgress } from '@vueuse/integrations/useNProgress';
import { ElMessage } from 'element-plus';
import { createRouter, createWebHistory } from 'vue-router';
import { HOME_URL, ROUTER_WHITE_LIST } from '@/config';
import { errorRouter, layoutRouter, staticRouter } from '@/routers/modules/staticRouter';
import store from '@/stores';
import { useUserStore } from '@/stores/modules/user';

const { start, done } = useNProgress(0, {
  showSpinner: false,
  trickleSpeed: 200,
  minimum: 0.3,
  easing: 'ease',
  speed: 500,
});

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [...layoutRouter, ...staticRouter, ...errorRouter],
  strict: false,
  scrollBehavior: () => ({ left: 0, top: 0 }),
});

// 路由前置守卫
router.beforeEach(
  async (
    to: RouteLocationNormalized,
    _from: RouteLocationNormalized,
    next: NavigationGuardNext,
  ) => {
    // 1、NProgress 开始
    start();

    // 2、标题
    document.title = (to.meta.title as string) || (import.meta.env.VITE_WEB_TITLE as string);

    // 3、权限 预留
    // 3、判断是访问登陆页，有Token访问当前页面，token过期访问接口，axios封装则自动跳转登录页面，没有Token重置路由到登陆页。
    // if (to.path.toLocaleLowerCase() === LOGIN_URL) {
    //   // 有Token访问当前页面
    //   if (userStore.token) {
    //     return next(from.fullPath);
    //   }
    //   else {
    //     ElMessage.error('账号身份已过期，请重新登录');
    //   }
    //   // 没有Token重置路由到登陆页。
    //   // resetRouter();  // 预留
    //   return next();
    // }

    const userStore = useUserStore(store);

    if (to.meta.requiresAuth && !userStore.token) {
      ElMessage.warning('请先登录后再访问知识库管理');
      userStore.openLoginDialog();
      return next({ path: HOME_URL, query: { redirect: to.fullPath } });
    }

    // 4、判断访问页面是否在路由白名单地址[静态路由]中，如果存在直接放行。
    if (ROUTER_WHITE_LIST.includes(to.path))
      return next();

    // 5、当前项目使用本地会话，不强制登录。

    // 6、正常访问页面。
    next();
  },
);

// 路由跳转错误
router.onError((error) => {
  // 结束全屏动画
  done();
  console.warn('路由错误', error.message);
});

// 后置路由
router.afterEach(() => {
  // 结束全屏动画
  done();
});

export default router;
