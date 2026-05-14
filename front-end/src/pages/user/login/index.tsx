import { LockOutlined, UserOutlined } from '@ant-design/icons';
import { LoginForm, ProFormCheckbox, ProFormText } from '@ant-design/pro-components';
import { Helmet, SelectLang, useIntl, useModel } from '@umijs/max';
import { Alert, App } from 'antd';
import { createStyles } from 'antd-style';
import React, { startTransition, useEffect, useRef, useState } from 'react';
import { Footer } from '@/components';
import { login } from '@/services/ant-design-pro/api';
import Settings from '../../../../config/defaultSettings';

declare global {
  interface Window {
    turnstile?: {
      render: (
        element: HTMLElement,
        options: {
          sitekey: string;
          callback: (token: string) => void;
          'expired-callback': () => void;
          'error-callback': () => void;
        },
      ) => string;
      remove: (widgetId: string) => void;
    };
  }
}

const TURNSTILE_SCRIPT_ID = 'cloudflare-turnstile-script';
const turnstileSiteKey = process.env.CLOUDFLARE_TURNSTILE_SITE_KEY || '';

const useStyles = createStyles(({ token }) => ({
  lang: {
    width: 42,
    height: 42,
    lineHeight: '42px',
    position: 'fixed',
    right: 16,
    borderRadius: token.borderRadius,
    ':hover': {
      backgroundColor: token.colorBgTextHover,
    },
  },
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    overflow: 'auto',
    backgroundImage:
      "url('https://mdn.alipayobjects.com/yuyan_qk0oxh/afts/img/V-_oS6r-i7wAAAAAAAAAAAAAFl94AQBr')",
    backgroundSize: '100% 100%',
  },
  turnstile: {
    display: 'flex',
    justifyContent: 'center',
    marginBottom: 24,
  },
}));

const Lang = () => {
  const { styles } = useStyles();

  return (
    <div className={styles.lang} data-lang>
      {SelectLang && <SelectLang />}
    </div>
  );
};

const LoginMessage: React.FC<{ content: string }> = ({ content }) => (
  <Alert style={{ marginBottom: 24 }} message={content} type="error" showIcon />
);

const TurnstileChallenge: React.FC<{
  siteKey: string;
  onTokenChange: (token: string) => void;
}> = ({ siteKey, onTokenChange }) => {
  const { styles } = useStyles();
  const containerRef = useRef<HTMLDivElement | null>(null);
  const widgetIdRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    if (!siteKey || !containerRef.current) {
      return undefined;
    }

    let cancelled = false;
    const renderTurnstile = () => {
      if (cancelled || !window.turnstile || !containerRef.current || widgetIdRef.current) {
        return;
      }

      widgetIdRef.current = window.turnstile.render(containerRef.current, {
        sitekey: siteKey,
        callback: onTokenChange,
        'expired-callback': () => onTokenChange(''),
        'error-callback': () => onTokenChange(''),
      });
    };

    const existingScript = document.getElementById(TURNSTILE_SCRIPT_ID) as HTMLScriptElement | null;
    if (existingScript) {
      renderTurnstile();
    } else {
      const script = document.createElement('script');
      script.id = TURNSTILE_SCRIPT_ID;
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.defer = true;
      script.onload = renderTurnstile;
      document.head.appendChild(script);
    }

    return () => {
      cancelled = true;
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = undefined;
      }
    };
  }, [onTokenChange, siteKey]);

  if (!siteKey) {
    return <Alert style={{ marginBottom: 24 }} type="warning" message="Cloudflare Turnstile site key is not configured." showIcon />;
  }

  return <div className={styles.turnstile} ref={containerRef} />;
};

const Login: React.FC = () => {
  const [userLoginState, setUserLoginState] = useState<API.LoginResult>({});
  const [turnstileToken, setTurnstileToken] = useState('');
  const { initialState, setInitialState } = useModel('@@initialState');
  const { styles } = useStyles();
  const { message } = App.useApp();
  const intl = useIntl();

  const getSafeRedirectUrl = (redirect: string | null): string => {
    if (!redirect?.startsWith('/') || redirect.startsWith('//')) {
      return '/';
    }

    try {
      const parsed = new URL(redirect, window.location.origin);
      if (parsed.origin !== window.location.origin) {
        return '/';
      }
      return `${parsed.pathname}${parsed.search}${parsed.hash}`;
    } catch {
      return '/';
    }
  };

  const fetchUserInfo = async () => {
    const userInfo = await initialState?.fetchUserInfo?.();
    if (userInfo) {
      startTransition(() => {
        setInitialState((s) => ({
          ...s,
          currentUser: userInfo,
        }));
      });
    }
  };

  const handleSubmit = async (values: API.LoginParams) => {
    if (turnstileSiteKey && !turnstileToken) {
      message.warning('Please complete the Cloudflare verification.');
      return;
    }

    try {
      const msg = await login({ ...values, type: 'account', turnstile_token: turnstileToken });
      if (msg.status === 'ok') {
        message.success(intl.formatMessage({ id: 'pages.login.success', defaultMessage: 'Login successful!' }));
        await fetchUserInfo();
        const urlParams = new URL(window.location.href).searchParams;
        window.location.href = getSafeRedirectUrl(urlParams.get('redirect'));
        return;
      }
      setUserLoginState(msg);
    } catch (error) {
      console.log(error);
      setUserLoginState({ status: 'error', type: 'account' });
      message.error(intl.formatMessage({ id: 'pages.login.failure', defaultMessage: 'Login failed, please try again!' }));
    }
  };

  return (
    <div className={styles.container}>
      <Helmet>
        <title>
          {intl.formatMessage({ id: 'menu.login', defaultMessage: 'Login' })}
          {Settings.title && ` - ${Settings.title}`}
        </title>
      </Helmet>
      <Lang />
      <div style={{ flex: '1', padding: '32px 0' }}>
        <LoginForm
          contentStyle={{ minWidth: 280, maxWidth: '75vw' }}
          logo={<img alt="logo" src="/logo.svg" />}
          title="KubeNeat"
          subTitle="Kubernetes YAML cleanup"
          initialValues={{ autoLogin: true }}
          onFinish={async (values) => {
            await handleSubmit(values as API.LoginParams);
          }}
        >
          {userLoginState.status === 'error' && (
            <LoginMessage content={intl.formatMessage({
              id: 'pages.login.accountLogin.errorMessage',
              defaultMessage: 'Invalid username or password.',
            })}
            />
          )}

          <ProFormText
            name="username"
            fieldProps={{ size: 'large', prefix: <UserOutlined /> }}
            placeholder={intl.formatMessage({ id: 'pages.login.username.placeholder', defaultMessage: 'Username' })}
            rules={[{ required: true, message: 'Please input your username.' }]}
          />
          <ProFormText.Password
            name="password"
            fieldProps={{ size: 'large', prefix: <LockOutlined /> }}
            placeholder={intl.formatMessage({ id: 'pages.login.password.placeholder', defaultMessage: 'Password' })}
            rules={[{ required: true, message: 'Please input your password.' }]}
          />

          <TurnstileChallenge siteKey={turnstileSiteKey} onTokenChange={setTurnstileToken} />

          <div style={{ marginBottom: 24 }}>
            <ProFormCheckbox noStyle name="autoLogin">
              {intl.formatMessage({ id: 'pages.login.rememberMe', defaultMessage: 'Remember me' })}
            </ProFormCheckbox>
          </div>
        </LoginForm>
      </div>
      <Footer />
    </div>
  );
};

export default Login;
