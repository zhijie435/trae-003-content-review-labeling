import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";

export const metadata: Metadata = {
  title: "双标注质检抽样平台",
  description: "基于双标注比对的内容审核质检抽样平台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        <div className="flex h-screen overflow-hidden bg-slate-50">
          <Sidebar />
          <main className="flex-1 overflow-auto">
            <div className="min-h-full">
              <header className="h-16 sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-slate-200 flex items-center px-6">
                <h1 className="text-lg font-semibold text-slate-800">
                  双标注质检抽样平台
                </h1>
              </header>
              <div className="p-6">{children}</div>
            </div>
          </main>
        </div>
      </body>
    </html>
  );
}
