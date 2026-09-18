/**
 * Hook to access the AI chat store.
 */

import { useContext } from "react";
// mobx store
import { StoreContext } from "@/lib/store-context";
// types
import type { IAIChatStore } from "@/store/ai";

export const useAIChat = (): IAIChatStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("useAIChat must be used within StoreProvider");
  return context.aiChat;
};
