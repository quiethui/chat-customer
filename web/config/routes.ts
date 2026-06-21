export default [
  {
    path: '/user',
    layout: false,
    routes: [
      {
        name: 'login',
        path: '/user/login',
        component: './user/login',
      },
    ],
  },
  {
    name: 'system-customer',
    icon: 'solution',
    path: '/system/customer',
    component: './system-customer',
    access: 'canAccess',
  },
  {
    name: 'agent-desk',
    icon: 'customerService',
    path: '/agent-desk',
    component: './agent-desk',
    access: 'canAccess',
  },
  {
    name: 'knowledge',
    icon: 'database',
    path: '/knowledge',
    component: './knowledge',
    access: 'canAdmin',
  },
  {
    name: 'system-manager',
    icon: 'team',
    path: '/system/manager',
    component: './system-manager',
    access: 'canAdmin',
  },
  {
    name: 'llm-log',
    icon: 'profile',
    path: '/system/llm-log',
    component: './llm-log',
    access: 'canAdmin',
  },
  {
    name: 'chatbot',
    icon: 'comment',
    path: '/chatbot',
    component: './chatbot',
    access: 'canAccess',
  },
  {
    path: '/welcome',
    name: 'welcome',
    icon: 'smile',
    hideInMenu: true,
    component: './Welcome',
  },
  {
    path: '/admin',
    name: 'admin',
    icon: 'crown',
    access: 'canAdmin',
    hideInMenu: true,
    routes: [
      {
        path: '/admin',
        redirect: '/admin/sub-page',
      },
      {
        path: '/admin/sub-page',
        name: 'admin.sub-page',
        component: './Admin',
      },
    ],
  },
  {
    name: 'list.table-list',
    icon: 'table',
    path: '/list',
    hideInMenu: true,
    component: './table-list',
  },
  {
    name: 'account.settings',
    icon: 'setting',
    path: '/account/settings',
    component: './account-settings',
    access: 'canAccess',
  },
  {
    path: '/',
    redirect: '/welcome',
  },
  {
    component: './exception/404',
    layout: false,
    path: './*',
  },
];
