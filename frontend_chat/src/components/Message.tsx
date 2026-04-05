import type { Message as MessageType } from '../types';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import AudioPlayer from './AudioPlayer';
import '../styles/message.css';

interface MessageProps {
  message: MessageType;
}

function Message({ message }: MessageProps) {
  return (
    <div className={`message ${message.role}`}>
      <div className="message-avatar">
        {message.role === 'user' ? '👤' : '🤖'}
      </div>
      <div className="message-content">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '');
              const isInline = !match && !className;
              return !isInline && match ? (
                <SyntaxHighlighter
                  style={oneDark}
                  language={match[1]}
                  PreTag="div"
                  customStyle={{
                    margin: '0.5rem 0',
                    borderRadius: '6px',
                    fontSize: '0.85rem',
                  }}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
              ) : (
                <code className={className} {...props}>
                  {children}
                </code>
              );
            },
            table({ children }) {
              return (
                <div className="table-wrapper">
                  <table>{children}</table>
                </div>
              );
            },
          }}
        >
          {message.content}
        </ReactMarkdown>

        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="tool-calls">
            <details>
              <summary>🔧 Used {message.tool_calls.length} tool(s)</summary>
              <div className="tool-calls-list">
                {message.tool_calls.map((tool, idx) => (
                  <div key={idx} className="tool-call-item">
                    <div className="tool-call-header">
                      <span className="tool-name">{tool.tool}</span>
                    </div>
                    <div className="tool-call-input">
                      <span className="tool-label">Input:</span>
                      <SyntaxHighlighter
                        style={oneDark}
                        language="json"
                        customStyle={{
                          margin: '0.25rem 0',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          padding: '0.5rem',
                        }}
                      >
                        {JSON.stringify(tool.input, null, 2)}
                      </SyntaxHighlighter>
                    </div>
                    {tool.result && (
                      <div className="tool-call-result">
                        <span className="tool-label">Result:</span>
                        <SyntaxHighlighter
                          style={oneDark}
                          language="json"
                          customStyle={{
                            margin: '0.25rem 0',
                            borderRadius: '4px',
                            fontSize: '0.75rem',
                            padding: '0.5rem',
                            maxHeight: '200px',
                            overflow: 'auto',
                          }}
                        >
                          {JSON.stringify(tool.result, null, 2)}
                        </SyntaxHighlighter>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}

        {/* Audio playback for assistant messages with TTS */}
        {message.role === 'assistant' && message.audioBlob && (
          <AudioPlayer audioBlob={message.audioBlob} />
        )}

        <div className="message-timestamp">
          {message.timestamp.toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}

export default Message;
