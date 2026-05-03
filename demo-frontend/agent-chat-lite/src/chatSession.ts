type EnsureConversationIdArgs = {
  selectedConversationId: string;
  selectedAgentId: string;
  createConversation: () => Promise<string>;
};

export async function ensureConversationId({
  selectedConversationId,
  selectedAgentId,
  createConversation,
}: EnsureConversationIdArgs): Promise<string> {
  if (selectedConversationId) {
    return selectedConversationId;
  }
  if (!selectedAgentId) {
    throw new Error('请先选择 Agent');
  }
  return createConversation();
}
