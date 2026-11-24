# AGENTS.md: BUSA 310 Final Project

Instructions for AI assistants working on this project. Read this before drafting anything. Update it whenever a rule, decision or section status changes.

## 1. Project overview

**Course:** BUSA 310, "From Prediction to Product: Build Your Own Startup" (Fall 2026).
**Team:** Long Pham, May Bui, Muhammad Rayyan Habib, Tra Vo.
**Goal:** Decide whether a predictive tool has a real market and could become a sustainable business. The model is only one part. The grade also depends on market evidence, a business plan and an honest treatment of risk.

### Deliverables
1. **Business Plan Book** (market research, financial projections, risks and ethics). Written as the team's Google Doc; drafts are produced one section at a time in chat.
2. **Working predictive product or prototype** (classification or regression on real-world data).
3. **Final group presentation.**
4. **Individual AI-free writing journal.** Each person writes their own. **Never write, draft, edit or "improve" a journal entry.**

### Schedule
- Nov 17 and Nov 24: in-class discussions and weekly plans
- **Dec 3: final presentations** (the cover page of the book is dated Dec 3, 2026)
- **Dec 9: final deadline**

### Assignment requirements to cover
- **Market research:** supply (existing solutions), demand (evidence from Google Trends, surveys, social media or literature), competitor analysis (why they succeeded or failed, how we differ).
- **Predictive product:** what the model predicts, how well it performs, how customers use it.
- **Business plan:** development and operating budget and how the money is raised; marketing strategy; revenue model; years to profitability; development timeline and milestones.
- **Risks and strategies:** what could cause failure, how we respond, how customer data is protected, AI ethics.

## 2. The business concept (decisions already made)

- **Product:** a mobile app that helps retailers (convenience stores, grocery delis, bakeries) forecast daily demand for freshly prepared food so they waste less and sell out less often.
- **Shopper side:** shoppers find discounted surplus food from nearby stores, reserve and pay in the app, and collect it before closing. Similar in features to Too Good To Go.
- **Donation:** food that still does not sell can be offered to partner charities and food banks. Order of priority: prevent waste (forecast), then sell surplus, then donate.
- **Launch market: Ho Chi Minh City, Vietnam.** Three of the four founders are based in Vietnam. Reasons: many convenience stores and local food businesses already sell fresh food daily, and students and workers seek affordable food late in the evening. These reasons must be backed by sources in the Market Assessment.
- **The model is developed and tested on public data from several countries** (U.S., Germany, Ecuador). The claim is that the *method* carries over to Vietnam once comparable local store data is collected. **It does not claim that Vietnamese accuracy is already proven.**
- **No store interviews or pilot diaries** (dropped by the team). Store-specific numbers are assumptions with sources and low/base/high cases, not measurements.
- **Prediction is on the seller side.** The shopper side is a marketplace and does not depend on the model.
- Revenue: retailer subscription plus a commission on shopper purchases; charities pay nothing. Prices are still undecided.
- Company name is still a placeholder: `[COMPANY NAME]`.

## 3. How to work on the Business Plan Book

### Workflow rules (set by the user)
1. **Write one section at a time.** Do not start the next section until the user approves the current one ("approve"). If they answer something else, resolve it, then ask for approval again.
2. **Do not add analysis on wording, format or graphics after every section.** Add short notes only when something needs the user's attention: an unverified claim, a missing number, a decision, or an assumption.
3. After approval, say which section is next and ask for any input that section needs.
4. Do not repeat content already covered in another section. The user flagged repetition twice. Keep the funding amount, the data-access risk and the milestone list in one main place each, and refer back.
5. The structure is the template in the course handout, adapted (see section 5). Keep the template's prompt questions above each section, in italics, as the user's own draft does.

### Writing style
- Professional, formal, concise prose. Numbered lists with a **bold lead-in** where the template asks several questions (for example "For Retailers:", "For Consumers:").
- **Be creative with wording and vary vocabulary.** These phrases are banned because they became repetitive:
  - "two-sided" and "dual-sided" (say "serves both retailers and shoppers", "both groups", "a network of stores and shoppers")
  - "ready-to-eat meals" (use "fresh food", "freshly prepared food", "prepared food", "surplus meals", "surplus food")
  - "end-of-day" (use "late-day", "near closing time", "before the store closes", "leftover")
  - Also avoid filler such as "seamlessly" and "effectively".
- Avoid "eliminate food waste"; say "reduce". Say "tested" until the cross-market model test is finished, then "validated" with the results beside it.
- Use bracketed placeholders for anything unknown: `[amount]`, `[date]`, `[number]`. The team fills them from the financial template.
- Do not guess pronouns for people. Use names or "they".

### Evidence and sourcing rules
- **Do not assume anything about the Vietnamese market.** State only what is sourced. Where the team needs a figure, leave a bracket and say what to research.
- Cite sources as markdown links. Flag figures that are self-reported by companies ("the company reports") or come from advocacy or sponsored material.
- Report conflicting figures as a range with sources (for example Ho Chi Minh City convenience-store counts differ by source and definition).
- Do not name specific laws, regulators or fees unless found in a source. Mark legal points `[confirm]` for a legal advisor.
- Search results are summaries. Tell the user when the full source was not read.
- Do not claim "no competitor exists in Vietnam". The finding is limited to: no launched Vietnamese surplus-food resale app was found in English and Vietnamese searches. It has not been checked in the app stores.
- The Gate 2 rule (Dec 3): cut any claim that has no source.

## 4. Section status (Business Plan Book)

| Section | Status |
|---|---|
| Vision/Mission Statement | Approved |
| Goals and Objectives | Approved (milestone dates and money are placeholders) |
| Key to Success | Approved |
| Company Summary: Objectives, Company Background | Approved (founder roles and milestone results pending) |
| Resources, Facilities and Equipment | Approved |
| Marketing Methods | Approved |
| Management and Organization | Approved (roles and titles are placeholders) |
| Ownership Structure | Approved (legal form and equity split pending) |
| Social Responsibility | Approved |
| Internal Analysis | Approved |
| Products and/or Services | Approved (model results and pricing pending) |
| Market Assessment: General Market, Customer Analysis, Strategic Alternatives | Drafted; accepted by moving on |
| Market Assessment: Industry Analysis and competitor table | Approved (includes Treatsure) |
| Strategic Implementation: Production, Resource Needs, Sourcing/Procurement, Marketing Strategy | Approved |
| **Strategic Implementation: Performance Standards** | **Drafted; awaiting approval** |
| Financial Plan (Financial Projections, Contingency Plan) | Not started. Needs the financial template. |
| Risks and Strategies (failure causes, responses, data protection, AI ethics) | Not started. Required by the assignment; decide where it sits in the book. |
| Executive Summary | Write last. Maximum two pages. Seven headings. |

### Edits already applied across sections
- Donation option added to Products and Services, Goals (For Charities), Company Background, Marketing Methods (alliances), Social Responsibility, and a donation-partner milestone.
- Company Summary "Objectives" should be one sentence about the funding goal only (no retelling of the product).
- The empty template line under the Company Summary heading is dropped.
- Treatsure added to the competitor table and the Industry Analysis.

## 5. Template adaptation

The template was written for agricultural businesses. Handle these questions briefly or replace them:
- Hedging, forward contracting, options, futures: "not applicable", with a one-line reason.
- Crop insurance: replace with professional liability, cyber and product-liability cover (to confirm with an advisor).
- Chemicals, noise, dust, odor: replace with data privacy, food safety, AI ethics, food-waste impact, community involvement.
- Yield, tillage, GPS, commodity organizations: replace with forecast accuracy, uptime, customer savings.
- Family and lifestyle (Internal Analysis): dropped.

## 6. Open decisions and placeholders

- Company name; each founder's role, title, university and background
- Legal form (Vietnam entity?) and equity split, vesting
- Funding target, funding sources, debt/equity mix, break-even year, first-year budget by category
- Retailer subscription price, shopper commission rate, recommended discount range
- Launch neighborhoods in Ho Chi Minh City; anchor partner (chain or hotel); first charity partner
- Technology stack (mobile framework, cloud provider, payment partners)
- Milestone dates for pilot, launch and growth
- Model results table and cross-market test results; Vietnam survey results

## 7. Research still to verify

- No launched Vietnamese surplus-food resale app: check Apple and Google app stores in Vietnam, and read the Vietnamese-language article on leftover-food apps that could not be opened.
- Ho Chi Minh City store counts: settle on one source and definition.
- Vietnamese legal requirements (Personal Data Protection Law, e-commerce law and its decrees, food-safety and donation rules): confirm from the primary texts or an advisor. No law protects food donors from liability, per policy reviews; verify.
- Self-reported performance claims (Afresh, Winnow, Leanpath, Masan, Yindii): cite as company-reported.
- Late-night shopper survey (60 percent of regular shoppers under 30): confirm the survey date.
- The team's own Vietnam consumer survey (50+ responses, Vietnamese shoppers): not yet run or analyzed.

## 8. Data and model

- **Task:** regression. Predict units sold per store, item or department and day.
- **Baseline:** same weekday last week. **Metric:** mean absolute error. Report waste and missed-sales effect from the backtest, with method notes.
- **Core data:** Dominick's (U.S. deli and bakery sales), Kiel bakery (Germany), Kroger Complete Journey (item patterns), Favorita (Ecuador, perishable flag; promoted to core for the cross-market test), Open-Meteo weather, calendar features (weekday, holidays, paydays).
- **Cross-market test:** train on one dataset, test on another. This is the main evidence that the method is market-independent.
- **Market data:** use Vietnamese sources (statistics office, OpenStreetMap for Ho Chi Minh City, Google Trends for Vietnam). The Indiana-based Census and ACS work is no longer the main market evidence.
- **Skip:** Walmart M5, FreshRetailNet, EIA, FSSA, FoodKeeper, BLS, FRED, FoodData Central, NRA, IPEDS, Food Access Atlas.
- **Scope for Dec 3:** a narrow working model plus mock-up screens for the retailer, shopper and donation flows. Vietnam, the shopper side and donation are shown as the roadmap, not as built features.
- Be upfront in all writing that Dominick's is U.S. data and that the Indiana and other public data prove the method, not Vietnamese accuracy.

## 9. Repository rules (from the team's Git guide)

- **Every change must be reviewed in a pull request before it reaches `main`.** No exceptions, including small edits to this file, documentation and data.
- Never work directly on `main`, and never push to `main`. Create a branch for each task, push the branch, and open a pull request with a clear title and description.
- **Always create a new branch when working independently**, meaning any task done on your own or in a separate session, and before making the first edit. Start from an up-to-date `main` and name it `yourname-short-description` (lowercase, hyphens). Check with `git branch` that you are not on `main` before editing.
- A teammate other than the author must review and approve the pull request. Assistants never approve or merge a pull request, and never merge on the author's behalf.
- Do not commit, push or open pull requests unless the user asks.
- If review requests changes, add new commits to the same branch. Do not force-push or open a replacement pull request.
- GitHub rejects files over 100 MB. Share large datasets by link.
- Prefer CSV to Excel. Keep raw data untouched and put cleaned data in a separate file.
- Never commit passwords, API keys or personal data.
- Do not rename or move shared files without telling the team.
- Never run `git push --force` or `git reset --hard` unless the user explicitly asks.
