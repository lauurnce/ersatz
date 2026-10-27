import { NOTICE } from "@/lib/notice";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col justify-center gap-4 px-4 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">Ersatz</h1>
      <p className="text-lg">Replacement parts you can verify.</p>
      <p className="text-sm opacity-80">
        Ersatz checks form, fit and function replacements for discontinued LDO regulators and
        op-amps. Every value links to the provider response or datasheet page it came from. The demo
        is not live yet.
      </p>
      <p role="note" className="border-l-2 pl-3 text-sm">
        {NOTICE}
      </p>
    </main>
  );
}
