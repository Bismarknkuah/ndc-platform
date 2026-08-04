"use client";

// Catches errors thrown by the ROOT layout itself (outside every other
// error boundary), so it must render its own <html>/<body> - see
// https://nextjs.org/docs/app/api-reference/file-conventions/error#global-error
export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body>
        <div
          style={{
            display: "flex",
            height: "100dvh",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 16,
            fontFamily: "system-ui, sans-serif",
            textAlign: "center",
            padding: 16,
          }}
        >
          <p style={{ fontSize: 24, fontWeight: 600 }}>The application failed to load</p>
          <p style={{ color: "#666", maxWidth: 360 }}>
            Please refresh the page. If this keeps happening, contact support.
          </p>
          <button
            onClick={reset}
            style={{
              padding: "8px 16px",
              borderRadius: 6,
              background: "#0e6b3e",
              color: "white",
              border: "none",
              cursor: "pointer",
            }}
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
