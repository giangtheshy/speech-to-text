import React, { useEffect, useRef, useState } from "react";

interface WebSocketStatus {
  connected: boolean;
  error: string | null;
}

const SpeechToText: React.FC = () => {
  const [transcript, setTranscript] = useState<string>("");
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [websocketStatus, setWebsocketStatus] = useState<WebSocketStatus>({ connected: false, error: null });
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const websocketRef = useRef<WebSocket | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError("Trình duyệt không hỗ trợ getUserMedia.");
      return;
    }
    if (typeof MediaRecorder === "undefined") {
      setError("Trình duyệt không hỗ trợ MediaRecorder.");
      return;
    }

    const wsUrl = "ws://localhost:8000/ws/transcribe";
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setWebsocketStatus({ connected: true, error: null });
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      const data = event.data;
      // Mỗi message nhận được là final result
      setTranscript((prev) => prev + data);
    };

    ws.onerror = (event: Event) => {
      console.error("WebSocket error:", event);
      setWebsocketStatus((prev) => ({ ...prev, error: "Lỗi kết nối WebSocket" }));
    };

    ws.onclose = (event) => {
      console.log("WebSocket disconnected:", event.reason);
      setWebsocketStatus({ connected: false, error: event.reason || "Đã ngắt kết nối." });
    };

    websocketRef.current = ws;

    return () => {
      if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
        websocketRef.current.close();
      }
      stopRecording();
    };
  }, []);

  const startRecording = async () => {
    if (!websocketRef.current || websocketRef.current.readyState !== WebSocket.OPEN) {
      setError("Không thể bắt đầu ghi âm: WebSocket chưa sẵn sàng.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioStreamRef.current = stream;

      // Sử dụng định dạng tương thích với ffmpeg: audio/webm; codecs=opus
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm; codecs=opus",
      });

      mediaRecorder.ondataavailable = (e) => {
        const chunk = e.data;
        if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
          const reader = new FileReader();
          reader.onload = () => {
            const arrayBuffer = reader.result;
            if (arrayBuffer && websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
              websocketRef.current.send(arrayBuffer);
            }
          };
          reader.readAsArrayBuffer(chunk);
        }
      };

      mediaRecorder.onerror = (evt: Event) => {
        const errorEvent = evt as unknown as { error?: DOMException };
        console.error("Lỗi MediaRecorder:", errorEvent.error);
        setError(`Lỗi MediaRecorder: ${errorEvent.error?.message || "Không xác định"}`);
      };

      mediaRecorder.start(1000);
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      setError(null);
      setTranscript(""); // Mỗi lần bắt đầu ghi âm mới, xóa transcript cũ
    } catch (err: any) {
      console.error("Lỗi truy cập microphone:", err);
      setError("Không thể truy cập microphone. Vui lòng kiểm tra quyền truy cập.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current = null;
    }
    if (audioStreamRef.current) {
      audioStreamRef.current.getTracks().forEach((track) => track.stop());
      audioStreamRef.current = null;
    }
    setIsRecording(false);
  };

  return (
    <div style={{ maxWidth: "600px", margin: "0 auto", padding: "20px", fontFamily: "sans-serif" }}>
      <h1>Realtime Speech to Text</h1>
      {error && <div style={{ color: "red", marginBottom: "10px" }}>Lỗi: {error}</div>}

      <div style={{ marginBottom: "10px" }}>
        <strong>Trạng thái WebSocket:</strong> {websocketStatus.connected ? "Đã kết nối" : "Chưa kết nối"}
        {websocketStatus.error && ` (Lỗi: ${websocketStatus.error})`}
      </div>

      <div style={{ marginBottom: "10px" }}>
        {isRecording ? (
          <button onClick={stopRecording}>Dừng ghi âm</button>
        ) : (
          <button onClick={startRecording} disabled={!websocketStatus.connected || !!websocketStatus.error || !!error}>
            Bắt đầu ghi âm
          </button>
        )}
      </div>

      <div>
        <h2>Kết quả:</h2>
        <p style={{ whiteSpace: "pre-wrap", border: "1px solid #ccc", padding: "10px", minHeight: "100px" }}>
          {transcript || (isRecording ? "Đang nhận diện..." : "")}
        </p>
      </div>
    </div>
  );
};

export default SpeechToText;
