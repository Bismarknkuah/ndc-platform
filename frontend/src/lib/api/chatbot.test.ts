import { describe, expect, it, vi, beforeEach } from "vitest";
import { apiClient } from "./client";
import * as chatbotApi from "./chatbot";

vi.mock("./client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./client")>();
  return {
    ...actual,
    apiClient: {
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
    },
  };
});

describe("chatbot API module", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("createConversation posts to the real endpoint with an optional title", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { id: "c1", title: "New conversation", is_active: true, created_at: "", updated_at: "" },
    });

    const result = await chatbotApi.createConversation();
    expect(apiClient.post).toHaveBeenCalledWith("/chatbot/conversations/", { title: undefined });
    expect(result.id).toBe("c1");
  });

  it("sendMessage posts to the conversation-scoped message endpoint", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        user_message: { id: "m1", role: "USER", body: "Hi", created_at: "" },
        assistant_message: { id: "m2", role: "ASSISTANT", body: "Hello!", created_at: "" },
      },
    });

    const result = await chatbotApi.sendMessage("c1", "Hi");
    expect(apiClient.post).toHaveBeenCalledWith("/chatbot/conversations/c1/messages/", {
      body: "Hi",
    });
    expect(result.assistant_message.body).toBe("Hello!");
  });

  it("archiveConversation calls delete on the conversation detail endpoint", async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({});
    await chatbotApi.archiveConversation("c1");
    expect(apiClient.delete).toHaveBeenCalledWith("/chatbot/conversations/c1/");
  });

  it("listMessages fetches the message list for a conversation", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { count: 0, num_pages: 1, current_page: 1, next: null, previous: null, results: [] },
    });
    await chatbotApi.listMessages("c1");
    expect(apiClient.get).toHaveBeenCalledWith("/chatbot/conversations/c1/messages/");
  });
});
