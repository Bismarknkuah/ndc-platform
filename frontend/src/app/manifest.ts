import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "NDC Party Platform",
    short_name: "NDC Platform",
    description:
      "Organizational management platform for the National Democratic Congress.",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#f7f8f7",
    theme_color: "#0e6b3e",
    orientation: "portrait-primary",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon-512-maskable.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
