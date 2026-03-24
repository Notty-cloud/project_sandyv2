# Software Requirements Specification (SRS)

**Project:** [Placeholder Name] – School Biometric Attendance & Security

---

## 1. Introduction

**Purpose:** This document defines the functional and non-functional requirements for the FR platform, a facial-recognition-based registration and safety system for schools.

**Scope:** The system includes a localized AI inference engine, a centralized management dashboard, and mobile alerting for security personnel.

**Definitions & Acronyms:**

| Term | Definition |
|------|------------|
| **FRVT** | Facial Recognition Vendor Test (NIST standard) |
| **BIPA** | Biometric Information Privacy Act |
| **Edge Computing** | Processing data on local school hardware rather than the cloud to ensure speed and privacy |
| **Vector Embedding** | A 512-dimensional numerical representation of a face |

---

## 2. Overall Description

**Product Perspective:** A high-security middleware that bridges physical IP cameras with existing Student Information Systems (SIS).

**Product Functions:**
- Rapid student check-in
- Real-time intruder/blacklist detection
- Automated attendance reporting

**User Classes:**

| Role | Responsibility |
|------|---------------|
| **Registrar** | Manage student rosters and consent forms |
| **Security Officers** | Receive mobile alerts for unauthorized entries |
| **System Admin** | Manage camera health and server uptime |

**Operating Environment:** Ubuntu-based Edge Servers (on-site) + React-based Web Dashboard (Cloud).

**Assumptions:** Reliable power supply at camera locations; school-wide high-speed LAN.

**Constraints:** Must operate within the strict legal frameworks of FERPA (US) and GDPR (EU).

---

## 3. System Features & Functional Requirements

### 3.1 User Registration & Authentication
- **Biometric Enrollment:** Capturing 3–5 images per student to account for lighting and growth.
- **Consent Management:** A digital portal for parents to grant/revoke biometric rights.

### 3.2 Dashboard & Visualization
- **Live Stream Overlay:** Visual "bounding boxes" around detected faces with identification labels.
- **Anomaly Reporting:** Flags if a student is detected in a location they shouldn't be (e.g., leaving a "geofenced" zone).

### 3.3 AI Implementation
- **Anti-Spoofing (Liveness):** Infrared (IR) or depth sensing to ensure a 2D photo isn't used to bypass security.
- **Bias Mitigation:** Regular auditing of the AI model to ensure equal accuracy across all skin tones and age groups.

---

## 4. Non-Functional Requirements

| Requirement | Detail |
|-------------|--------|
| **Performance** | Cold Start detection speed $< 1.5$s; Warm matching speed $< 500$ms |
| **Security** | Salted Vector Embeddings — database theft cannot be reverse-engineered into a human face |
| **Reliability & Availability** | 99.9% uptime; local storage buffer for logs if internet is lost |
| **Scalability** | Multi-Campus management from a single master account |

---

## 5. External Interface Requirements

- **UI:** Minimalist "Traffic Light" interface for entry points (Green = OK, Yellow = Unknown, Red = Alert).
- **Software Interfaces:** Plug-and-play integration with PowerSchool, Infinite Campus, Skyward, Google Classroom, and Microsoft Active Directory.
- **Communication Interfaces:** Secure SMTP for automated parent notifications when a student arrives.

---

## 6. Data Requirements

- **Data Types:** Structured JSON for logs; binary vectors for biometrics.
- **Data Integrity:** Checksums to ensure biometric templates aren't corrupted during sync.
- **Data Retention:** Automated purge scripts that delete biometric data for graduated or withdrawn students every 30 days.

---

## 7. Security & Compliance Requirements

- **Physical Security:** Edge servers must be housed in locked racks.
- **Legal Compliance:** Explicit "Right to be Forgotten" workflows for parents.

---

## 8. Quality Attributes

- **Adaptability:** Ability to recognize students even with partial occlusions (e.g., masks, glasses, or hats).
- **Transparency:** System must provide "Explainable AI" logs showing why a certain confidence score was assigned.

---

## 9. Acceptance Criteria

- **User Acceptance (UAT):** 10/10 test students recognized within 2 seconds.
- **Security Audit:** Zero "Critical" vulnerabilities found in a 3rd-party pen-test.

---

## 10. Future Enhancements

- **Behavioral Analysis:** Detecting aggressive movements or falls in hallways.
- **Visitor Management:** QR-code + face pairing for temporary visitor passes.
