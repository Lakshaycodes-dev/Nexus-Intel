import Image from "next/image";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface LogoProps {
  href?: string;
  className?: string;
}

const logoAsset = {
  src: "/nexus-intel-logo.png",
  width: 980,
  height: 254,
} as const;

export function NexusMark({ className }: { className?: string }) {
  return (
    <Image
      src={logoAsset.src}
      alt="Nexus Intel"
      width={logoAsset.width}
      height={logoAsset.height}
      className={cn("h-8 w-auto object-contain", className)}
    />
  );
}

export function Logo({ href = "/", className }: LogoProps) {
  return (
    <Link
      href={href}
      aria-label="Nexus Intel home"
      className={cn(
        "group inline-flex items-center rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2",
        className,
      )}
    >
      <Image
        src={logoAsset.src}
        alt=""
        width={logoAsset.width}
        height={logoAsset.height}
        className="h-9 w-auto object-contain sm:h-10"
      />
    </Link>
  );
}
