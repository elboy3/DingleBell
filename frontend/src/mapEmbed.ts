/** Keyless Google Maps embed URL, shared by ListingDetail and Swipe so the
 * zoom level (and query construction) only needs to be tuned in one place. */
export function mapEmbedUrl(address: string, neighborhood: string | null): string {
  const query = encodeURIComponent(`${address}, ${neighborhood || ""} Brooklyn, NY`);
  // z=15 - a couple notches out from the default address-lookup zoom, which
  // crops in tight enough to lose the surrounding streets/context.
  return `https://maps.google.com/maps?q=${query}&z=15&output=embed`;
}
