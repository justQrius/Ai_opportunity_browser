
# Product Requirements Document: The AI Opportunity Browser

## 1. Overview & Vision

**1.1. Vision:** To become the definitive resource for entrepreneurs and investors seeking to build high-growth, AI-native ventures. We do this by systematically identifying, validating, and presenting real-world business problems that are primed for an AI-powered solution.

**1.2. Problem:** Building a successful startup is incredibly risky. A primary reason for failure is building a solution for a problem that doesn't exist or isn't painful enough for customers to pay for. For AI startups, this risk is compounded by technical complexity and the challenge of finding a true, defensible "AI Edge." Entrepreneurs need more than just ideas; they need **conviction**.

**1.3. Solution:** The AI Opportunity Browser is a web platform that provides a curated gallery of market-validated business opportunities. Each opportunity consists of a validated problem, a blueprint for an AI-native solution, and a dossier of the evidence that proves the market's demand. We replace guesswork with evidence, providing builders with a de-risked foundation for their next venture.

**1.4. Target Audience:**
*   **Primary:** Experienced tech professionals, second-time founders, and product managers looking to start an AI-native company.
*   **Secondary:** Venture capitalists, angel investors, and corporate strategy teams seeking validated, data-driven insights into emerging market needs.

---

## 2. Goals & Success Metrics

**2.1. Business Goals:**
*   Establish the platform as the go-to starting point for building an AI venture.
*   Create a high-value, defensible data asset about early-stage market opportunities.
*   Achieve a subscription-based revenue model.

**2.2. Product Goals:**
*   Provide users with a steady stream of high-quality, validated opportunities.
*   Build user trust through transparency of evidence and a rigorous validation process.
*   Foster an engaged community of builders and validators.

**2.3. Key Success Metrics:**
*   **Engagement:** Weekly Active Users (WAU), Number of "Opportunity Saves" per user.
*   **Quality:** Average "Market Conviction Score" of published opportunities.
*   **Conversion:** Free-to-Paid subscription conversion rate.
*   **Community:** Number of active Validators, average number of stakes/challenges per opportunity in the Validation Market.

---

## 3. Features & Functionality

This PRD covers the core product, which includes the public-facing browser and the underlying engine.

#### **3.1. The Public AI Opportunity Browser (The User-Facing Product)**

*   **F-1: Opportunity Gallery:** A clean, browsable, and searchable gallery of "Opportunity Cards." Users can filter by Solution Archetype (e.g., `Insight Extraction`, `Workflow Automation`), industry, and other tags.
*   **F-2: The Opportunity Card:** The core unit of the product. Each card is a detailed report with a consistent, scannable structure.
    *   **F-2.1: At-a-Glance Dashboard:** Displays the key metrics at the top of the report:
        *   **Market Conviction Score (1-100):** A weighted score representing the overall viability of the opportunity.
        *   **AI Feasibility (Easy, Medium, Hard):** Technical difficulty of building the core AI.
        *   **Data Moat Potential (Low, Medium, High):** The potential for the AI to create a sustainable competitive advantage.
        *   **Tags:** Solution Archetype, target industry, etc.
    *   **F-2.2: The Report Body:**
        *   **Validated Problem:** A clear description of the problem, leading with a summary of the evidence.
        *   **AI-Native Solution:** A blueprint of the proposed AI product.
        *   **The AI Edge:** An explanation of *why* AI fundamentally transforms the solution.
        *   **Go-to-Market Headstart:** Actionable advice on finding the first ten customers.
    *   **F-2.3: The Evidence Locker:** A transparent, non-gated section showing the anonymized snippets of evidence (user complaints, job postings, etc.) that support the validation claims.
*   **F-3: User Accounts & Subscription:**
    *   **Free Tier:** Users can browse all opportunity headlines and the "At-a-Glance Dashboard."
    *   **Premium Tier (Subscription):** Users get full access to the detailed report body, including the Evidence Locker and Go-to-Market Headstart. Premium users can also "Save" and organize opportunities.

#### **3.2. The Underlying Engine (The "Opportunity Validation Ecosystem")**

This is the internal system that powers the browser.

*   **E-1: The "Scout" Layer (Signal Acquisition):**
    *   A system of specialized AI agents ("Scouts") will continuously scan pre-defined data sources (freelance sites, B2B review sites, professional communities, SEC filings).
    *   The system must be able to automatically find and cluster related signals from different sources, generating a "Signal Density Score" for each cluster.
*   **E-2: The "Blueprint Factory" (Automated Analysis):**
    *   An automated pipeline that takes high-density Signal Clusters and transforms them into structured "Venture Candidate" packages.
    *   This includes modules for: problem definition, AI solution mapping, data moat analysis, and a first-pass "Economic Viability Analysis" (market sizing, price point anchoring).
*   **E-3: The "Validation Market" (Crowdsourced HITL):**
    *   A private, internal platform where vetted human experts ("Validators") review the Venture Candidates generated by the Blueprint Factory.
    *   **E-3.1: Validator Profiles & Reputation:** Validators will have profiles and a "Reputation Score."
    *   **E-3.2: Staking & Challenging:** The system must support two core actions:
        *   **Backing:** Validators can stake reputation points on candidates they believe in.
        *   **Breaking:** Validators can submit a formal "Fatal Flaw" challenge to a candidate.
    *   The system's logic must reward validators for accurate backing and successful challenges, creating a "skin in the game" incentive structure.
*   **E-4: The "Market Conviction Score" Algorithm:**
    *   An algorithm that calculates the final score for each opportunity based on its initial Signal Density Score and its performance in the Validation Market. An opportunity must exceed a minimum MCS threshold to be published.

---

## 4. Design & UX

*   **Look & Feel:** Clean, professional, data-driven, and minimalist. The design should inspire confidence and clarity, similar to high-quality financial reporting tools.
*   **Core Principle:** Data visualization is key. The At-a-Glance Dashboard should be highly scannable. The Evidence Locker should present proof in a clear, undeniable way.

---

## 5. Future Considerations & Potential Roadmap

*   **Personalization:** Allow users to create a profile of their skills and experience to get a personalized "Founder Fit" score for each opportunity.
*   **API Access:** Offer paid API access to the opportunity data for VC firms and corporate clients.
*   **Founder-Validator Connect:** Create a feature to allow premium subscribers to connect with the top Validators who backed a specific opportunity.
*   **Generative Assets:** Explore adding a "Generate Pitch Deck" or "Generate Landing Page" feature based on the opportunity data, as a premium add-on.
