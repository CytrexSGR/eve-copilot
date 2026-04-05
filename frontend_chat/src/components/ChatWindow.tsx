import { useEffect, useRef } from 'react';
import type { ChatContext } from '../types';
import { useAgentChat } from '../hooks/useAgentChat';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { Loader2, Wrench } from 'lucide-react';
import '../styles/chat.css';

interface ChatWindowProps {
  context: ChatContext;
}

function ChatWindow({ context }: ChatWindowProps) {
  const {
    messages,
    isStreaming,
    currentTool,
    error,
    sendMessage,
  } = useAgentChat(context.sessionId, context.characterId);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const handleSendMessage = async (message: string) => {
    await sendMessage(message);
  };

  return (
    <div className="chat-window">
      <div className="chat-header">
        <div className="connection-status">
          {isStreaming ? (
            <>
              <Loader2 size={14} className="spinning" />
              {currentTool ? (
                <span className="tool-indicator">
                  <Wrench size={12} />
                  {currentTool}
                </span>
              ) : (
                'Thinking...'
              )}
            </>
          ) : (
            <>
              <span className="status-dot connected"></span>
              Ready
            </>
          )}
        </div>
        {error && <div className="error-indicator">⚠️ {error}</div>}
      </div>

      <MessageList messages={messages} isTyping={isStreaming && !currentTool} />
      <div ref={messagesEndRef} />

      <ChatInput onSendMessage={handleSendMessage} disabled={isStreaming} />
    </div>
  );
}

export default ChatWindow;
