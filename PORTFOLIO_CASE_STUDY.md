# Project Sandy — Facial Recognition School Attendance

**Live:** https://projectsandyv2-production.up.railway.app
**Code:** https://github.com/Notty-cloud/project_sandyv2
**Stack:** Django REST Framework · PostgreSQL + pgvector · DeepFace (Facenet512) · Docker · Railway · React

**My role:** backend API, face-matching pipeline, database schema and deployment,
on a six-person capstone team. The React client was built by teammates; where a
fix below crossed into it, I have said so.

---

## The problem

Schools in Barbados still take attendance on paper. A teacher spends the first
minutes of every period reading names aloud, records go missing, and nobody can
answer "how often was this student late last term?" without leafing through a
register.

Project Sandy replaces the register with a camera: a student looks at a laptop
and attendance is recorded in about a second.

## What the system does

- Enrol a student's face once, recognise them on any later morning
- Mark attendance against a class, flagging late arrivals automatically
- Manual override when recognition fails, with an audit trail
- Role-based access: Head Teacher, Coordinator, Teacher
- Import a whole roster from the school's existing CSV export

---

## Selected engineering work

### Measuring match accuracy instead of trusting a default

The pipeline compares 512-dimension face embeddings by cosine similarity. One
threshold decides whether two photos are the same person: too low and the wrong
student is marked present, too high and nobody is recognised at all.

Rather than accept a library default, I measured against real faces on the
deployed system:

| Comparison | Score |
|---|---|
| Same person, two captures minutes apart | **0.84** |
| Two different people | **0.48** |
| Threshold in use | **0.65** |

The cutoff sits between the two distributions with margin either side. That is
the difference between "it seems to work" and being able to say why.

### A false positive those numbers exposed

While testing, an unenrolled person came back as a confirmed match at 0.48 —
above the 0.30 the client was actually sending, below the 0.65 the interface
displayed. The API had honoured exactly what it was sent; the fault was that
the threshold existed in two places and they disagreed.

I traced it from the measurement, and the fix made one value authoritative
across the API contract and the client. (The client change was in a teammate's
area; the diagnosis and the contract were mine.)

### Enrolment that verifies identity, not just "a face"

Enrolment checked that a photo *contained* a face, never *whose*. Any face
could be filed under any student — a student could enrol themselves under a
friend's record and have the system mark that friend present every morning,
which defeats the point of the system.

I found this by enrolling my own face under three different student names and
noticing the recognition results could not be reconciled. Enrolment now rejects
a photo that does not match the student's existing photos, and one that already
belongs to a different student, naming the conflict. A coordinator-level
override exists because a genuinely poor first photo has to be correctable.

Nine tests cover accept, mismatch, duplicate, override, override-denied, tenant
scoping and backend separation.

### Multi-tenancy that is actually enforced

Every record carries a `tenant_id`, but nothing enforced it. The API filtered on
a tenant supplied by the *client*, so omitting the parameter returned every
school's students. The face endpoints read the tenant from the request body,
letting a caller match faces against another school's roster, and the
account-unlock route fetched by id with no tenant check at all.

Scoping now derives from the authenticated account, ignores client-supplied
values, and fails closed: an indeterminate tenant returns nothing rather than
everything. Because it runs through the queryset, it governs detail routes too —
another tenant's record is a 404, not an object you can edit.

### Query count, measured before and after

Listing students issued one `COUNT` per row:

```
before:  200 students → 201 queries
after:   200 students →   1 query
```

Each of those was a network round-trip to the database. The regression test
asserts the *shape* — adding students must not add queries — rather than a fixed
number that would break on unrelated changes while missing the bug that matters.

Fixing it surfaced a worse one: the API ignored `page_size`, so every list was
capped at 50 with no pagination in the UI. A school importing 500 students would
have seen the first 50 and nothing indicating the rest existed — which reads as
though the import lost records.

### A timezone constant that broke the core feature

Attendance decides late-versus-present from local wall-clock time. The project
was configured `Asia/Manila` while the schools are in Barbados — twelve hours
apart. A student arriving 07:00 was evaluated as 19:00 and marked late. Every
punctual student, every day, with no error anywhere.

Fixed, made per-deployment configurable, and pinned with a test that reproduces
the original failure so the reason for the setting is recorded rather than
folklore.

### Two face backends, kept comparable

The repository contained a second, unused ONNX pipeline (SCRFD + ArcFace)
alongside the production DeepFace one. Rather than delete it, I put both behind
one interface selected by environment variable, and wrote a benchmark that
reports *separation* — mean same-person similarity minus mean different-person
similarity — so the choice can rest on measurement.

The constraint that shaped the design: Facenet512 and ArcFace embed into
different vector spaces. Both are 512-dimensional, so they fit the same column,
but a similarity between them is meaningless noise. Every embedding records the
backend that produced it and matching only ever compares within one, so the two
can coexist without silently corrupting results.

---

## Testing

117 tests, running in about a minute: the enrol / identify / mark-attendance
endpoints, tenant isolation, CSV parsing, backup round-trips, transport security
headers.

The suite originally took **56 minutes**. The cause was not the tests — a
missing Redis meant every cache call opened a socket that took two seconds to be
refused, and the login throttle touches the cache on most requests. Tests now use
an in-process cache: 56 minutes to 42 seconds. A suite nobody runs prevents
nothing, and most of the bugs above reached production precisely because there
was no suite worth running.

## Deployment

Dockerised and deployed to Railway with PostgreSQL and HTTPS. Getting there
surfaced four faults that only appear in a clean container:

- `deepface` pulls in the GUI build of OpenCV, which links against X11 libraries
  a slim image does not carry
- a missing `tf-keras` shim that happened to be present in local virtualenvs
- an unpinned OpenCV resolving to 5.0, which removed the API the default face
  detector uses — it imported fine and would have failed at the first enrolment
- model weights downloading inside a request on every cold start, now baked into
  the image at build time

The build now asserts its own assumptions, so a wrong OpenCV version fails the
build rather than shipping an image that breaks on first use.

Face embeddings cannot be regenerated without physically re-enrolling every
student, so I also wrote a portable export/restore that round-trips between
PostgreSQL and SQLite, with tests asserting the vectors survive bit-for-bit.
