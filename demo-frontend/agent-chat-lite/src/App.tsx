import { FormEvent, useEffect, useMemo, useRef, useState } from 'react';

type Agent = {
  _id: string;
  name: string;
  hermesProfile: string;
};

type Conversation = {
  _id: string;
  title: string | null;
  createdAt: string;
};

type Message = {
  _id: string;
  conversationId: string;
  text: string;
  role: 'user' | 'assistant';
  createdAt: string;
  files?: MessageFile[];
};

type LoginResponse = {
  accessToken: string;
  email: string;
  name: string;
};

type MessageFile = {
  filename: string;
  originalName?: string;
  mimetype?: string;
  size?: number;
  url?: string;
};

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export default function App() {
  const [email, setEmail] = useState('admin@admin.com');
  const [password, setPassword] = useState('123456');
  const [token, setToken] = useState<string | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversationId, setSelectedConversationId] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [pickedFiles, setPickedFiles] = useState<File[]>([]);
  const [input, setInput] = useState('');
  const [streamingReply, setStreamingReply] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  const selectedConversation = useMemo(
    () => conversations.find((c) => c._id === selectedConversationId) ?? null,
    [conversations, selectedConversationId]
  );

  async function authedFetch(url: string, init?: RequestInit): Promise<Response> {
    const headers = new Headers(init?.headers);
    if (token) headers.set('Authorization', `Bearer ${token}`);
    const resp = await fetch(url, { ...init, headers });
    if (resp.status === 401) {
      setToken(null);
      setAgents([]);
      setConversations([]);
      setMessages([]);
      throw new Error('登录已过期，请重新登录');
    }
    return resp;
  }

  async function login(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const resp = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!resp.ok) {
      setError('登录失败，请检查账号密码');
      return;
    }
    const data = (await resp.json()) as LoginResponse;
    setToken(data.accessToken);
  }

  async function loadAgents() {
    const resp = await authedFetch('/api/agent');
    if (!resp.ok) throw new Error(`加载 Agent 失败: ${resp.status}`);
    const data = (await resp.json()) as { items: Agent[] };
    const rows = data.items ?? [];
    setAgents(rows);
    if (!rows.length) {
      setSelectedAgentId('');
      return;
    }
    setSelectedAgentId((prev) => (rows.some((a) => a._id === prev) ? prev : rows[0]._id));
  }

  async function loadConversations(agentId: string) {
    if (!agentId) return;
    const resp = await authedFetch(`/api/conversation/agent/${agentId}`);
    if (!resp.ok) throw new Error(`加载会话失败: ${resp.status}`);
    const data = (await resp.json()) as { items: Conversation[] };
    const rows = data.items ?? [];
    setConversations(rows);
    setSelectedConversationId((prev) => (rows.some((c) => c._id === prev) ? prev : rows[0]?._id ?? ''));
  }

  async function createConversation() {
    if (!selectedAgentId) return;
    const resp = await authedFetch('/api/conversation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ agentId: selectedAgentId }),
    });
    if (!resp.ok) throw new Error(`新建会话失败: ${resp.status}`);
    const data = (await resp.json()) as Conversation;
    await loadConversations(selectedAgentId);
    setSelectedConversationId(data._id);
  }

  async function loadMessages(conversationId: string) {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    const resp = await authedFetch(`/api/message/conversation/${conversationId}`);
    if (!resp.ok) throw new Error(`加载消息失败: ${resp.status}`);
    const data = (await resp.json()) as { items: Message[] };
    setMessages(data.items ?? []);
  }

  async function sendMessage(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!selectedConversationId || (!text && !pickedFiles.length) || isSending) return;
    setError(null);
    setInput('');
    setIsSending(true);
    setStreamingReply('');
    const optimistic: Message = {
      _id: `tmp-${Date.now()}`,
      conversationId: selectedConversationId,
      text,
      role: 'user',
      createdAt: new Date().toISOString(),
      files: pickedFiles.map((f) => ({
        filename: f.name,
        originalName: f.name,
        size: f.size,
        url: (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name,
      })),
    };
    setMessages((prev) => [...prev, optimistic]);

    const body = new FormData();
    body.set('conversationId', selectedConversationId);
    body.set('text', text);
    pickedFiles.forEach((file) => body.append('files', file));
    setPickedFiles([]);

    try {
      const resp = await authedFetch('/api/message/chat', { method: 'POST', body });
      if (!resp.ok || !resp.body) throw new Error(`发送失败: ${resp.status}`);
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let done = false;
      while (!done) {
        const part = await reader.read();
        done = part.done;
        buffer += decoder.decode(part.value || new Uint8Array(), { stream: !done });
        const chunks = buffer.split('\n\n');
        buffer = chunks.pop() ?? '';
        for (const chunk of chunks) {
          const line = chunk
            .split('\n')
            .find((l) => l.startsWith('data: '))
            ?.slice(6);
          if (!line) continue;
          if (line === '[DONE]') continue;
          const parsed = safeJson(line);
          if (!parsed || typeof parsed !== 'object') continue;
          const payload = parsed as Record<string, unknown>;
          if (
            payload.type === 'response.output_text.delta' &&
            typeof payload.delta === 'string'
          ) {
            setStreamingReply((prev) => prev + payload.delta);
          }
          if (payload.type === 'response.error' && typeof payload.delta === 'string') {
            setError(payload.delta);
          }
        }
      }
      await loadMessages(selectedConversationId);
    } catch (err) {
      setError(err instanceof Error ? err.message : '发送失败');
    } finally {
      setIsSending(false);
      setStreamingReply('');
    }
  }

  useEffect(() => {
    if (!token) return;
    void loadAgents().catch((err) => setError(err instanceof Error ? err.message : '加载 Agent 失败'));
  }, [token]);

  useEffect(() => {
    if (!token || !selectedAgentId) return;
    void loadConversations(selectedAgentId).catch((err) =>
      setError(err instanceof Error ? err.message : '加载会话失败')
    );
  }, [token, selectedAgentId]);

  useEffect(() => {
    if (!token || !selectedConversationId) return;
    void loadMessages(selectedConversationId).catch((err) =>
      setError(err instanceof Error ? err.message : '加载消息失败')
    );
  }, [token, selectedConversationId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, streamingReply]);

  if (!token) {
    return (
      <div className="page centered auth-page">
        <form className="card login glass" onSubmit={login}>
          <h1>Agent Chat Lite</h1>
          <p className="hint">极简对话台：选 Agent、开聊、上传附件。</p>
          <label className="field">
            <span>Email</span>
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="field">
            <span>Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button type="submit" className="primary">
            登录
          </button>
          {error ? <p className="error">{error}</p> : null}
        </form>
      </div>
    );
  }

  return (
    <div className="page app-page">
      <aside className="sidebar">
        <div className="card block glass">
          <h2>Agent</h2>
          <select
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
            disabled={!agents.length}
          >
            {agents.map((a) => (
              <option key={a._id} value={a._id}>
                {a.name} ({a.hermesProfile})
              </option>
            ))}
          </select>
        </div>

        <div className="card block glass">
          <div className="title-row">
            <h2>会话</h2>
            <button type="button" className="primary" onClick={() => void createConversation()}>
              新建
            </button>
          </div>
          <ul className="list">
            {conversations.map((c) => (
              <li key={c._id}>
                <button
                  type="button"
                  className={c._id === selectedConversationId ? 'active' : ''}
                  onClick={() => setSelectedConversationId(c._id)}
                >
                  {c.title || `会话 ${c._id.slice(0, 8)}`}
                </button>
              </li>
            ))}
            {!conversations.length ? <li className="empty">暂无会话</li> : null}
          </ul>
        </div>
      </aside>

      <main className="chat">
        <div className="card chat-header glass">
          <div>
            <strong>{selectedConversation?.title || '未命名会话'}</strong>
            <p className="subtle">
              {selectedConversationId ? `会话 ID: ${selectedConversationId}` : '请选择会话'}
            </p>
          </div>
          <button
            type="button"
            className="secondary"
            onClick={() => setToken(null)}
          >
            退出
          </button>
        </div>

        <div className="card messages glass">
          {messages.map((m) => (
            <div key={m._id} className={`msg ${m.role}`}>
              <div className="role">{m.role === 'user' ? '你' : '助手'}</div>
              <div className="bubble">{m.text}</div>
              {m.files?.length ? (
                <div className="files">
                  {m.files.map((f, idx) => (
                    <div className="file-row" key={`${m._id}-f-${idx}`}>
                      <span className="file-name">{f.originalName || f.filename}</span>
                      {f.url ? <code className="file-path">{f.url}</code> : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          ))}
          {isSending && streamingReply ? (
            <div className="msg assistant">
              <div className="role">助手</div>
              <div className="bubble">{streamingReply}</div>
            </div>
          ) : null}
          {!messages.length ? <div className="empty">发送第一条消息开始对话</div> : null}
          <div ref={endRef} />
        </div>

        <form className="card composer glass" onSubmit={sendMessage}>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入消息，或者仅上传文件..."
            disabled={!selectedConversationId || isSending}
            rows={3}
          />
          <div className="composer-row">
            <label className="file-picker">
              <input
                type="file"
                multiple
                disabled={!selectedConversationId || isSending}
                onChange={(e) => setPickedFiles(Array.from(e.target.files || []))}
              />
              选择文件
            </label>
            <button
              className="primary"
              type="submit"
              disabled={
                !selectedConversationId || (!input.trim() && !pickedFiles.length) || isSending
              }
            >
              {isSending ? '发送中...' : '发送'}
            </button>
          </div>
          {pickedFiles.length ? (
            <div className="picked-files">
              {pickedFiles.map((file, idx) => {
                const rel = (file as File & { webkitRelativePath?: string }).webkitRelativePath;
                return (
                  <div key={`${file.name}-${idx}`} className="file-row">
                    <span className="file-name">{file.name}</span>
                    <code className="file-path">{rel || file.name}</code>
                  </div>
                );
              })}
            </div>
          ) : null}
        </form>
        {error ? <p className="error">{error}</p> : null}
      </main>
    </div>
  );
}
