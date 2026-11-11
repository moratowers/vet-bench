# vet-bench pilot: the pre-registration

These five files are the pilot's frozen plan and its four addenda, copied word for word from the project's private repository. They are not edited here, so their hashes can be checked against the ones the write-up cites. They mention some private folders by name; those folders are not public.

| File | sha256 | Committed (UTC) |
|---|---|---|
| `PREREG.md` (revision 20, frozen) | `055b7380089dcf9b5a5ea1f9715f8f9fd31ccfffce1455e7d052d7bf9cbf9f02` | 2026-11-09T02:13:10Z |
| `PREREG_ADDENDUM_A.md` (usage-limit rule) | `dfb27e76a70959762c27aa6395f721c26e7b0f1703ad1445a0b96862ae0b2ab1` | 2026-11-09T02:35:43Z |
| `PREREG_ADDENDUM_B.md` (API-error rule) | `c87b143a5d6d3b06d151d619288756a64b61a777552bfd57050c3d5850d9a161` | 2026-11-09T15:45:06Z |
| `PREREG_ADDENDUM_C.md` (re-issued grading batch) | `6e9534a8389e70a585fc6f3b64cd121088f9c0c8236b075e98cd6835487a8446` | 2026-11-10T00:25:19Z |
| `PREREG_ADDENDUM_D.md` (private family labels) | `46e84fe450b2db03cf2ff12995a78c8905298f6d21db2e3e8984d0803d48697f` | 2026-11-10T01:22:52Z |

Check a file with `shasum -a 256 prereg/PREREG.md`. The blinding seed is the first 8 hex digits of the plan's hash read as an integer: `055b7380` is 89879424.

Times are the private repository's commit times, which come after each file was written; each addendum's own header gives the time it was written. The plan froze at 2026-11-09T02:11:55Z, before any main run. Addendum A came before any smoke or main run, and B before the main runs resumed. C came during grading and D after scoring; each says what it changes and why. The write-up is at [moratowers.dev/vet-bench](https://moratowers.dev/vet-bench/).
