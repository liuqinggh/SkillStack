import { describe, expect, it, vi } from 'vitest';

import { ensureConversationId } from './chatSession';

describe('ensureConversationId', () => {
  it('returns the existing conversation id without creating a new one', async () => {
    const createConversation = vi.fn(async () => 'new-conversation');

    await expect(
      ensureConversationId({
        selectedConversationId: 'existing-conversation',
        selectedAgentId: 'claim',
        createConversation,
      })
    ).resolves.toBe('existing-conversation');

    expect(createConversation).not.toHaveBeenCalled();
  });

  it('creates a conversation on first send when none exists yet', async () => {
    const createConversation = vi.fn(async () => 'created-conversation');

    await expect(
      ensureConversationId({
        selectedConversationId: '',
        selectedAgentId: 'claim',
        createConversation,
      })
    ).resolves.toBe('created-conversation');

    expect(createConversation).toHaveBeenCalledOnce();
  });

  it('rejects when no agent is selected', async () => {
    const createConversation = vi.fn(async () => 'created-conversation');

    await expect(
      ensureConversationId({
        selectedConversationId: '',
        selectedAgentId: '',
        createConversation,
      })
    ).rejects.toThrow('请先选择 Agent');
  });
});
