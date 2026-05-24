# Implementer pitfalls — detailed reference

Patterns multiple teammates stumbled into across past sessions. Either include these in the spawn prompt or have Implementers self-check.

## 1. Never embed literal control characters in source (especially NULL bytes)

### What goes wrong

When an Implementer writes a NULL-byte rejection test, they may intend an escape sequence like `'foo\x00bar'`, but **via the Edit/Write tool the `\x00` part gets expanded into a literal 0x00 byte and saved to the source file**. The fallout:

- git classifies the file as binary and shows `Bin N -> M bytes` (when NULL appears in the first 8000 bytes)
- PR diffs become invisible, so reviewers can't inspect the test contents
- grep / sourcegraph / similar tools won't hit it
- The `file` command labels it as `data`

### Correct form

In source, **always write the escape sequence as 4 characters** (`\`, `x`, `0`, `0`, 4 bytes):

```ts
// ❌ Bad: literal NULL byte (1 byte) gets embedded in source
expect(() => f({ id: 'foo<NUL>bar' })).toThrow(); // <NUL> is 0x00 1 byte

// ✅ Good: escape sequence (4 chars) compiles to 0x00 1 byte at runtime
expect(() => f({ id: 'foo\x00bar' })).toThrow();
```

Some Edit-tool implementations expand `\x00` when passed via `new_string`, so in those cases **rewriting the file from scratch with the Write tool is safer**.

The same applies to other control characters (`\x01`-`\x1F`, `\x7F`, `\x80`-`\x9F`) — write them as escape sequences, not literals.

### Verification command before commit

Before requesting a commit from the Lead, the Implementer must verify that no literal control bytes exist in the test source:

```bash
python3 -c "
import sys
with open('lib/<your-module>/.../test.unit.test.ts','rb') as f:
    d = f.read()
print([(i, hex(d[i])) for i in range(len(d)) if d[i] < 32 and d[i] not in (9, 10, 13)])
"
# → [] (empty list) is the pass condition
```

Pass condition: zero `< 32` bytes other than TAB (9) / LF (10) / CR (13). If any are detected, replace them with escape sequences via Edit / Write, then request a commit.

### Real incidents (observed across prior waves)

- One wave (a rate-limit / compat test): a line near the middle of the file contained a literal 0x00 → git binary-classified the file → Reviewer flagged Important → separate fix commit required
- Another wave (a retention / grace-period test): same pattern in a different test file
- Another wave (an inbox / list-component test): same pattern again
- Subsequent waves with the preventive measure (escape sequence + pre-commit check): zero occurrences

## 2. Other frequent pitfalls

### Do not run `git add -A` / `git add .` / `git add -u`

They drag in off-target files. Always specify paths: `git add lib/<your-module>/foo.ts lib/<your-module>/__tests__/foo.test.ts`.

That said, since Implementers are forbidden from git writes, in the commit request to the Lead, state explicitly "please add these files".

### Do not edit other people's files "on the way"

Editing off-target files (owned by other Implementers) "while you're at it" is forbidden. It scrambles ownership and breeds race conditions. If you want it fixed, report to the Lead via SendMessage — the owning Implementer or the Lead decides.

### Do not forget defense against NaN / Infinity / negative inputs

Validate inputs at the boundary using `Number.isFinite`. Silent fallback (silently replacing with 0 etc.) is forbidden; fail-closed `throw` is the rule.

### Document units in JSDoc

Document units like ms / bytes / % / deg / rad / KiB / count in JSDoc. There is past Reviewer Critical history around "gradient angle unit" confusion.

### Don't put raw input / secrets in output

Never include raw user input / orgKey / userId / secrets in Error.message / log output. Express these as paths, lengths, counts, or fixed indicators instead.
