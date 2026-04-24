import { permanentRedirect } from "next/navigation";

/** La ficha país vive en `/`; se mantiene `/espana` por enlaces antiguos. */
export default function EspanaRedirectPage() {
  permanentRedirect("/");
}
