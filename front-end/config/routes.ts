export default [
  {
    path: '/user',
    layout: false,
    routes: [
      {
        path: '/user/login',
        name: 'login',
        component: './user/login',
      },
      {
        path: '/user/register',
        name: 'register',
        icon: 'userAdd',
        component: './user/register',
      },
      {
        path: '/user/register-result',
        name: 'register-result',
        icon: 'checkCircle',
        component: './user/register-result',
      },
      {
        path: '/user',
        redirect: '/user/login',
      },
      {
        path: '/user/*',
        redirect: '/user/login',
      },
    ],
  },
  {
    path: '/kubeneat',
    name: 'kubeneat',
    icon: 'fileDone',
    component: './kubeneat',
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    icon: 'dashboard',
    routes: [
      {
        path: '/dashboard',
        redirect: '/dashboard/analysis',
      },
      {
        name: 'tasks',
        icon: 'profile',
        path: '/dashboard/tasks',
        component: './dashboard/tasks',
      },
    ],
  },
  {
    name: 'account',
    icon: 'user',
    path: '/account',
    routes: [
      {
        path: '/account',
        redirect: '/account/center',
      },
      {
        name: 'center',
        icon: 'user',
        path: '/account/center',
        component: './account/center',
      },
      {
        name: 'settings',
        icon: 'setting',
        path: '/account/settings',
        component: './account/settings',
      },
    ],
  },
  {
    path: '/',
    redirect: '/kubeneat',
  },
  {
    path: '/*',
    redirect: '/kubeneat',
  },
];
