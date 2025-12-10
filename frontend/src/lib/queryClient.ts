import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 數據在 1 分鐘內視為新鮮，不會重新請求
      staleTime: 1000 * 60,
      // 數據在 5 分鐘後被垃圾回收
      gcTime: 1000 * 60 * 5,
      // 視窗重新聚焦時不自動重新請求
      refetchOnWindowFocus: false,
      // 重試 3 次
      retry: 3,
      // 指數退避重試延遲
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});
