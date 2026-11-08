// One file upload. The UI calls start(), cancel() and retry(); the transport calls onDone() and onError().
const MAX_ATTEMPTS = 3;

export function createUpload(transport, schedule) {
  const upload = { status: "idle", attempts: 0 };

  function send() {
    upload.status = "uploading";
    upload.attempts += 1;
    transport.send();
  }

  return {
    get status() { return upload.status; },
    start() {
      if (upload.status === "idle") send();
    },
    cancel() {
      if (upload.status === "uploading" || upload.status === "waiting") upload.status = "cancelled";
    },
    onDone() {
      if (upload.status === "uploading") upload.status = "done";
    },
    onError() {
      if (upload.status !== "uploading") return;
      if (upload.attempts < MAX_ATTEMPTS) {
        upload.status = "waiting";
        // Retry after a short wait. The timer is not cleared on cancel.
        schedule(() => send(), 1000);
      } else {
        upload.status = "failed";
      }
    },
    retry() {
      if (upload.status === "failed") {
        upload.attempts = 0;
        send();
      }
    },
  };
}
