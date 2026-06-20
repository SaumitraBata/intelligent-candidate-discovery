import { useEffect, useRef, useState, useCallback } from "react";

export function useWebSocket(sessionId) {
  const [progress, setProgress] = useState(null);
  const wsRef = useRef(null);

  const connect = useCallback(() => {
    if (!sessionId) return;

    const wsUrl = `ws://localhost:8000/ws/${sessionId}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => console.log("WS connected:", sessionId);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setProgress(data);
      } catch (e) {
        console.error("WS parse error:", e);
      }
    };

    ws.onclose = () => console.log("WS closed");
    ws.onerror = (e) => console.error("WS error:", e);

    wsRef.current = ws;
  }, [sessionId]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { progress, disconnect };
}