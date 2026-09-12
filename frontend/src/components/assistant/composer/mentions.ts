export type Mentionable = { name: string; role: string };

/** The caret sits in an @mention when the text ends with one. */
export function mentionQuery(text: string): string | null {
  const match = /(?:^|\s)@([\p{L}\d_-]*)$/u.exec(text);
  return match ? (match[1] ?? "").toLowerCase() : null;
}

export function matchMentions(
  text: string,
  people: readonly Mentionable[],
): Mentionable[] {
  const query = mentionQuery(text);
  if (query === null) return [];
  return people.filter((person) => person.name.toLowerCase().startsWith(query));
}

/** Replaces the trailing @mention with the chosen name and a trailing space. */
export function applyMention(text: string, name: string): string {
  return text.replace(/@[\p{L}\d_-]*$/u, `@${name} `);
}
