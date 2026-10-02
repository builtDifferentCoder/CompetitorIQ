/**
 * Streaming fetch consumer for POST-initiated Server-Sent Events (SSE).
 * Handles chunk buffering, named event parsing ('event: ...\ndata: ...\n\n'),
 * and distinguishes between graceful stream completion ('done' event) vs unexpected drops.
 */

export interface SSECallbacks {
  onEvent: (eventName: string, data: any) => void;
  onError: (error: Error) => void;
  onDone?: () => void;
}

export async function consumeSSEStream(
  url: string,
  body: Record<string, any>,
  callbacks: SSECallbacks,
  signal?: AbortSignal
): Promise<void> {
  let hasReceivedDoneEvent = false;

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(body),
      signal,
    });

    if (!response.ok) {
      let errorMsg = `Server responded with ${response.status} ${response.statusText}`;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) {
          errorMsg = typeof errorJson.detail === "string" ? errorJson.detail : JSON.stringify(errorJson.detail);
        }
      } catch {
        // Fall back to default status text
      }
      throw new Error(errorMsg);
    }

    if (!response.body) {
      throw new Error("Response body is null; cannot read event stream.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // SSE frames are delimited by double newlines (\n\n or \r\n\r\n)
      const blocks = buffer.split(/\r?\n\r?\n/);
      // The last element may be an incomplete frame still being buffered
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        if (!block.trim()) continue;

        const lines = block.split(/\r?\n/);
        let currentEvent = "message";
        const dataLines: string[] = [];

        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trim());
          }
        }

        if (dataLines.length > 0) {
          const rawData = dataLines.join("\n");
          let parsedData: any;
          try {
            parsedData = JSON.parse(rawData);
          } catch {
            parsedData = rawData;
          }

          if (currentEvent === "done") {
            hasReceivedDoneEvent = true;
          }

          callbacks.onEvent(currentEvent, parsedData);
        }
      }
    }

    // Process any remainder in buffer
    if (buffer.trim()) {
      const lines = buffer.split(/\r?\n/);
      let currentEvent = "message";
      const dataLines: string[] = [];
      for (const line of lines) {
        if (line.startsWith("event:")) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLines.push(line.slice(5).trim());
        }
      }
      if (dataLines.length > 0) {
        const rawData = dataLines.join("\n");
        let parsedData: any;
        try {
          parsedData = JSON.parse(rawData);
        } catch {
          parsedData = rawData;
        }
        if (currentEvent === "done") {
          hasReceivedDoneEvent = true;
        }
        callbacks.onEvent(currentEvent, parsedData);
      }
    }

    if (!hasReceivedDoneEvent && !signal?.aborted) {
      // Stream closed before receiving terminal 'done' event
      console.warn("SSE stream closed by server before 'done' event was received.");
    }

    callbacks.onDone?.();
  } catch (err: any) {
    if (err.name === "AbortError") {
      // Normal intentional user abort
      return;
    }
    callbacks.onError(err instanceof Error ? err : new Error(String(err)));
  }
}
