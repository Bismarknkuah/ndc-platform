"use client";

/** Reads a File into a raw base64 string (no "data:" prefix) - matches
 * the backend's base64-in-Mongo convention used for photos throughout
 * (collation sheets, candidate photos, receipts, media). */
export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const base64 = result.split(",")[1] ?? "";
      resolve(base64);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
