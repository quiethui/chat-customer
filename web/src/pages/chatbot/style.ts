// src/pages/chatbot/style.ts
import { createStyles } from 'antd-style';

export const useStyles = createStyles(({ css, token }) => ({
  layout: css`
    display: flex;
    flex: 1;
    overflow: hidden;
  `,

  sidebar: css`
    width: 260px;
    background: ${token.colorBgContainer};
    border-right: 1px solid ${token.colorBorderSecondary};
    display: flex;
    flex-direction: column;
    overflow: hidden;
  `,

  main: css`
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 0;
    background: ${token.colorBgContainer};
  `,

  messages: css`
    flex: 1;
    overflow-y: auto;
    padding: ${token.paddingMD}px;
    display: flex;
    flex-direction: column;
    align-items: center;

    > * {
      width: 100%;
    }
  `,

  footer: css`
    padding: ${token.paddingMD}px;
    border-top: 1px solid ${token.colorBorderSecondary};
    display: flex;
    justify-content: center;
  `,

  footerCenter: css`
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: ${token.paddingLG}px;
    gap: 32px;
    margin-top: -10%;
  `,

  welcomeTitle: css`
    font-size: 32px;
    font-weight: 600;
    color: ${token.colorText};
    text-align: center;
  `,

  senderArea: css`
    width: 100%;
    max-width: 940px;
    display: flex;
    flex-direction: column;
    gap: ${token.paddingSM}px;
  `,

  controls: css`
    display: flex;
    align-items: center;
    gap: ${token.marginXS}px;
    color: ${token.colorText};
    font-size: ${token.fontSize}px;
  `,

  cursor: css`
    animation: chatbot-blink 0.8s step-end infinite;

    @keyframes chatbot-blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0; }
    }
  `,

  references: css`
    margin-top: ${token.marginXS}px;
    font-size: ${token.fontSizeSM}px;
    color: ${token.colorTextTertiary};

    summary {
      cursor: pointer;
      user-select: none;
    }
  `,

  referenceItem: css`
    margin-top: ${token.marginXXS}px;
    padding: ${token.paddingXXS}px ${token.paddingXS}px;
    background: ${token.colorFillQuaternary};
    border-radius: ${token.borderRadiusSM}px;
    white-space: pre-wrap;
    word-break: break-word;
  `,
}));
