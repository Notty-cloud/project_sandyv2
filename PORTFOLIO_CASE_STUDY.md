# Project Sandy — Facial Recognition School Attendance

> Draft case study for a personal portfolio. Adapt the voice, and see the
> "Honesty checklist" at the end before publishing.

**Live:** https://projectsandyv2-production.up.railway.app
**Code:** https://github.com/Notty-cloud/project_sandyv2
**Stack:** React · Django REST Framework · PostgreSQL + pgvector · DeepFace (Facenet512) · Docker · Railway

---

## The problem

Schools in Barbados still take attendance on paper. A teacher spends the first
ten minutes of every period reading names aloud, records get lost, and nobody
can answer "how often was this student late last term?" without leafing through
a register.

Project Sandy replaces the register with a camera: a student looks at a laptop,
and attendance is recorded in about a second.

## What it does

- Enrol a student's face once; recognise them on any later morning
- Mark attendance against a class, automatically flagging late arrivals
- Manual override when recognition fails, with a full audit trail
- Role-based access: Head Teacher, Coordinator, Teacher
- Bulk-import a whole roster from the school's existing CSV export

---

## Engineering decisions worth talking about

### 1. Measuring accuracy instead of trusting it

Face matching compares 512-dimension embeddings by cosine similarity. The
threshold decides whether two photos are the same person — set it too low and
you mark the wrong student present; too high and nobody is recognised.

Rather than accept a library default, I measured on real faces:

| Comparison | Score |
|---|---|
| Same person, two photos minutes apart | **0.84** |
| Two different people | **0.48** |
| Threshold in use | **0.65** |

The cutoff sits between the two with margin on both sides. That is the
difference between "it seems to work" and knowing why.

### 2. A bug the numbers exposed

During testing an unenrolled person was reported as a confirmed match at 0.48.
Two separate faults: the UI sent a threshold of 0.3 while displaying 0.65, and
the "Match Confirmed" panel rendered on the presence of a result rather than on
the score clearing the cutoff — it asserted 0.48 was above 0.65 while showing a
red cross beside the same number.

Both now derive from one constant, so the interface cannot claim a score passed
a threshold it did not.

### 3. Enrolment verifies identity, not just "a face"

Enrolment originally checked that a photo *contained* a face, never *whose*.
Any face could be filed under any student — a student could enrol themselves
under a friend's record and have the system mark that friend present every
morning, which defeats the point of the system.

Enrolment now rejects a photo that does not match the student's existing
photos, and one that already belongs to a different student, naming the
conflict. A coordinator-level override exists because a genuinely poor first
photo has to be correctable.

### 4. A timezone constant that broke the core feature

Attendance decides late-versus-present from local wall-clock time. The project
was configured for `Asia/Manila` while the schools are in Barbados — twelve
hours apart. A student arriving at 07:00 was evaluated as 19:00 and marked
late. Every punctual student, every day, with no visible error.

Fixed, and pinned with a test that reproduces the original failure so the
reason for the setting is recorded rather than folklore.

### 5. Query count, measured before and after

Listing students ran one `COUNT` per row — 201 queries for a 200-student
roster. Replaced with a single aggregate:

```
before:  200 students → 201 queries
after:   200 students →   1 query
```

The regression test asserts the *shape* — adding students must not add queries
— rather than a fixed number that would break on unrelated changes while
missing the bug that matters.

### 6. Multi-tenancy that is actually enforced

Every record carries a `tenant_id`, but nothing enforced it: the API filtered
on a tenant supplied by the *client*, so omitting the parameter returned every
school's students. The face endpoints took the tenant from the request body,
letting a caller match faces against another school's roster.

Scoping now derives from the authenticated account, ignores client-supplied
values, and fails closed — an indeterminate tenant returns nothing rather than
everything. Ten tests cover cross-tenant reads, writes, updates and deletes.

---

## Testing

117 tests running in about a minute, covering the enrol / identify /
mark-attendance endpoints, tenant isolation, CSV parsing, backup round-trips
and the security headers.

The suite originally took **56 minutes**. The cause was not the tests: a
missing Redis meant every cache call opened a socket that took two seconds to
be refused. Tests now use an in-process cache — 56 minutes to 42 seconds. A
suite nobody runs prevents nothing.

## Deployment

Dockerised and deployed to Railway with PostgreSQL and HTTPS. Getting there
surfaced four bugs that only appear in a clean container: a GUI build of
OpenCV pulled in transitively that needs X11 libraries a slim image lacks, a
missing `tf-keras` shim that happened to be installed locally, an OpenCV 5
resolution that removed the API the face detector depends on, and model
weights downloading inside a request on every cold start.

The build now asserts its own assumptions, so a wrong OpenCV version fails the
build rather than shipping an image that breaks on first use.

---

## Honesty checklist before publishing

- [ ] **Team credit.** This was a six-person capstone. Say so, and be specific
      about which parts are yours. "I owned the backend API, face-matching
      pipeline and deployment" reads far better than an implied solo build —
      and any interviewer will ask.
- [ ] **Demo credentials.** Do not publish the admin password. Create a
      read-only demo account, or record a two-minute video instead.
- [ ] **Real student data.** Face embeddings are biometric data. Use your own
      face or a teammate's in any screenshot, with permission.
- [ ] **Numbers.** Keep them. They are the most credible thing here, and they
      are yours because you measured them.
