/** 输入区：文本框 + 发送，Enter 发送、Shift+Enter 换行。 */

import { useState } from 'react';

interface ComposerProps {
  disabled?: boolean;
  placeholder?: string;
  onSend: (text: string) => void;
}

export function Composer({ disabled, placeholder, onSend }: ComposerProps) {
  const [value, setValue] = useState('');

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
  };

  return (
    <div className="aics-composer">
      <textarea
        className="aics-input"
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        rows={2}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            submit();
          }
        }}
      />
      <button className="aics-send" type="button" disabled={disabled} onClick={submit}>
        发送
      </button>
    </div>
  );
}
