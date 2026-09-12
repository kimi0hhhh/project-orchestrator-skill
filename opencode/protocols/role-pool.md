<!-- OpenCode 版：由 tools/build_opencode.py 生成 -->

# 角色池（Role Pool）· agency-agents

> **用途**：7 个固定角色（`agents/00~06` 契约）覆盖不到时，主 Agent 从这里选**专项外援**。
> **怎么用**：`grep -i <关键词> .opencode/protocols/role-pool.md` → 读 `.opencode/role-pool/<slug>.md` 取完整人设 → 按下面纪律派发。
> **来源**：github.com/msitarzewski/agency-agents ｜ 已装 **279** 个到 `.opencode/role-pool/`（全部按团队归入下表）｜ 生成：2026-09-11
>
> 本文件是**索引快照**，不是契约：人设以 `.opencode/role-pool/<slug>.md` 为准。
> 上游更新后重新同步人设目录，再重建本索引（重建脚本未随包提供；索引表由人设目录的 slug 逐条生成）。
> OpenCode 包已**随包携带这 279 份人设**到 `.opencode/role-pool/`，无需本机预装。

---

## 使用纪律（三条，与 `capability-map.md` §7 一致）

1. **外援不承担门禁**：PASS/CONCERN/FAIL 只由体系内固定角色判；外援产物一律作为**输入/建议**，
   由对应固定角色吸收进工件（各角色分工见 `capability-map.md`）。
2. **派发两条路**（优先第 1 条，不依赖会话加载）：
   - **推荐**：task 工具的 `general` 子 agent + 把该角色人设文件的关键段落贴进 prompt，
     并**叠加本体系纪律**（`handoff-schema.md` §4 回传信号、`cli.py` 上报、`runtime/**` 禁改）。
   - 备选：新会话里角色已加载时，直接 该 slug 作为 task 的 `agent` 名（安装器把 frontmatter name 写成了 slug）。
3. **范围与预算**：外援计入并行 ≤3；同一任务**最多派 1 个外援**；不得为"顺便看看"派外援
   （角色池最大的风险是让范围悄悄膨胀）。派发前在 prompt 里写明：**它的产出交给谁吸收**。


### Engineering（`engineering`，64 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `ai-data-remediation-engineer` | AI Data Remediation Engineer | Specialist in self-healing data pipelines — uses air-gapped local SLMs and semantic… |
| `ai-engineer` | AI Engineer | Expert AI/ML engineer specializing in machine learning model development, deployment, and… |
| `api-platform-engineer` | API Platform Engineer | Expert API platform engineer for public and partner APIs — contract-first design… |
| `ats-validator-architect` | ATS Validator Architect | Architect and validator for Applicant Tracking Systems (ATS) and resume parsers. Combines… |
| `autonomous-optimization-architect` | Autonomous Optimization Architect | Intelligent system governor that continuously shadow-tests APIs for performance while… |
| `backend-architect` | Backend Architect | Senior backend architect specializing in scalable system design, database architecture,… |
| `china-network-engineer` | China Network Engineer | Expert in mainland China's mainstream enterprise networking stacks — Huawei VRP, H3C… |
| `cms-developer` | CMS Developer | Drupal and WordPress specialist for theme development, custom plugins/modules, content… |
| `code-reviewer` | Code Reviewer | Expert code reviewer who provides constructive, actionable feedback focused on… |
| `codebase-onboarding-engineer` | Codebase Onboarding Engineer | Expert developer onboarding specialist who helps new engineers understand unfamiliar… |
| `data-engineer` | Data Engineer | Expert data engineer specializing in building reliable data pipelines, lakehouse… |
| `data-visualization-engineer` | Data Visualization Engineer | Expert data visualization engineer — chart-type selection by data and question,… |
| `database-optimizer` | Database Optimizer | Expert database specialist focusing on schema design, query optimization, indexing… |
| `database-reliability-engineer` | Database Reliability Engineer | Expert database reliability engineer (DBRE) — high availability and replication, automated… |
| `desktop-app-engineer` | Desktop App Engineer | Expert desktop application engineer for Electron and Tauri — secure IPC and process… |
| `developer-tooling-engineer` | Developer Tooling Engineer | Expert developer-tooling and CLI engineer — building command-line tools and internal… |
| `devops-automator` | DevOps Automator | Expert DevOps engineer specializing in infrastructure automation, CI/CD pipeline… |
| `drupal-performance-engineer` | Drupal Performance Engineer | Expert Drupal 10/11 performance engineer specializing in Core Web Vitals, render and… |
| `drupal-shopping-cart-engineer` | Drupal Shopping Cart Engineer | Expert Drupal e-commerce engineer specializing in Drupal Commerce for product catalog… |
| `email-intelligence-engineer` | Email Intelligence Engineer | Expert in extracting structured, reasoning-ready data from raw email threads for AI agents… |
| `embedded-firmware-engineer` | Embedded Firmware Engineer | Specialist in bare-metal and RTOS firmware - ESP32/ESP-IDF, PlatformIO, Arduino, ARM… |
| `feishu-integration-developer` | Feishu Integration Developer | Full-stack integration expert specializing in the Feishu (Lark) Open Platform — proficient… |
| `filament-optimization-specialist` | Filament Optimization Specialist | Expert in restructuring and optimizing Filament PHP admin interfaces for maximum usability… |
| `finops-engineer` | FinOps Engineer | Expert cloud cost engineer for AWS/GCP/Azure — cost allocation and tagging, rightsizing,… |
| `frontend-developer` | Frontend Developer | Expert frontend developer specializing in modern web technologies, React/Vue/Angular… |
| `gaussdb-expert-engineer` | GaussDB Expert Engineer | Expert database specialist focusing on GaussDB OLTP — Huawei's self-developed… |
| `git-workflow-master` | Git Workflow Master | Expert in Git workflows, branching strategies, and version control best practices… |
| `identity-access-engineer` | Identity & Access Engineer | Expert identity engineer for OAuth 2.0/OIDC flows, enterprise SSO (SAML/OIDC) and SCIM… |
| `incident-response-commander` | Incident Response Commander | Expert incident commander specializing in production incident management, structured… |
| `internationalization-engineer` | Internationalization Engineer | Expert i18n engineer for ICU MessageFormat, CLDR plural rules, RTL and bidirectional… |
| `iot-fleet-engineer` | IoT Fleet Engineer | Expert IoT and edge fleet engineer — device provisioning and identity, MQTT/telemetry… |
| `it-service-manager` | IT Service Manager | Expert IT service management specialist using ITIL 4 framework for service catalog design,… |
| `knowledge-graph-engineer` | Knowledge Graph Engineer | Structures information and capabilities into interconnected nodes (entities) and edges… |
| `llm-post-training-engineer` | LLM Post-Training Engineer | Evidence-driven owner for SFT, preference optimization, RLHF/RLVR, MoE post-training, and… |
| `minimal-change-engineer` | Minimal Change Engineer | Engineering specialist focused on minimum-viable diffs — fixes only what was asked,… |
| `mobile-app-builder` | Mobile App Builder | Specialized mobile application developer with expertise in native iOS/Android development… |
| `mobile-release-engineer` | Mobile Release Engineer | Expert mobile release and distribution engineer for iOS and Android — code signing,… |
| `multi-agent-systems-architect` | Multi-Agent Systems Architect | Systems architect specializing in the design, coordination, and governance of multi-agent… |
| `network-engineer` | Network Engineer | Expert network engineer for Cisco IOS/IOS-XE, Cisco ASA/FTD, Juniper Junos, and Palo Alto… |
| `orgscript-engineer` | OrgScript Engineer | Expert in designing, parsing, and implementing OrgScript grammar, AST validation, and… |
| `payments-billing-engineer` | Payments & Billing Engineer | Expert payments engineer for PSP integrations (Stripe, Adyen, Braintree, PayPal),… |
| `pdf-engine-architect` | PDF Engine Architect | Architect and specialist in deterministic HTML-to-PDF document compilation, Playwright… |
| `platform-engineer` | Platform Engineer | Expert internal developer platform (IDP) engineer specializing in golden paths, paved… |
| `privacy-engineer` | Privacy Engineer | Expert privacy engineer who implements privacy in code — PII discovery and classification,… |
| `prompt-engineer` | Prompt Engineer | Specialist in crafting, testing, and systematically optimizing prompts for LLMs — turning… |
| `rag-pipeline-engineer` | RAG Pipeline Engineer | Production RAG specialist focused on chunking strategy, retrieval quality, hybrid search,… |
| `rapid-prototyper` | Rapid Prototyper | Specialized in ultra-fast proof-of-concept development and MVP creation using efficient… |
| `realtime-collaboration-engineer` | Realtime Collaboration Engineer | Expert realtime systems engineer for WebSocket/SSE infrastructure, presence, CRDT and… |
| `rust-refactoring-specialist` | Rust Refactoring Specialist | Expert Rust engineer for repository-scale refactoring, safe renames, module restructuring,… |
| `search-relevance-engineer` | Search Relevance Engineer | Expert search engineer for Elasticsearch and OpenSearch — index and analyzer design, BM25… |
| `section-508-accessibility-specialist` | Section 508 Accessibility Specialist | Expert U.S. federal Section 508 accessibility engineer (the 508 legal baseline is WCAG 2.0… |
| `senior-developer` | Senior Developer | Premium implementation specialist - Masters Laravel/Livewire/FluxUI, advanced CSS,… |
| `software-architect` | Software Architect | Expert software architect specializing in system design, domain-driven design,… |
| `solidity-smart-contract-engineer` | Solidity Smart Contract Engineer | Expert Solidity developer specializing in EVM smart contract architecture, gas… |
| `sre-site-reliability-engineer` | SRE (Site Reliability Engineer) | Expert site reliability engineer specializing in SLOs, error budgets, observability, chaos… |
| `technical-writer` | Technical Writer | Expert technical writer specializing in developer documentation, API references, README… |
| `universal-document-compiler` | Universal Document Compiler | Architect of schema-agnostic document ASTs, algorithmic data-shape layout inference,… |
| `uswds-developer` | USWDS Developer | Expert U.S. Web Design System frontend developer specializing in USWDS components and… |
| `video-streaming-engineer` | Video Streaming Engineer | Expert video streaming engineer for adaptive bitrate delivery — HLS/DASH packaging, ffmpeg… |
| `voice-ai-integration-engineer` | Voice AI Integration Engineer | Expert in building end-to-end speech transcription pipelines using Whisper-style models… |
| `webassembly-engineer` | WebAssembly Engineer | Expert WebAssembly engineer — compiling Rust/C++/Go to Wasm, JS interop and the boundary… |
| `wechat-mini-program-developer` | WeChat Mini Program Developer | Expert WeChat Mini Program developer specializing in 小程序 development with WXML/WXSS/WXS,… |
| `wordpress-performance-engineer` | WordPress Performance Engineer | Expert WordPress performance engineer specializing in Core Web Vitals, object caching… |
| `wordpress-shopping-cart-engineer` | WordPress Shopping Cart Engineer | Expert WordPress e-commerce engineer specializing in WooCommerce for product catalog… |

### Specialized（`specialized`，59 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `accounts-payable-agent` | Accounts Payable Agent | Autonomous payment processing specialist that executes vendor payments, contractor… |
| `agentic-identity-trust-architect` | Agentic Identity & Trust Architect | Designs identity, authentication, and trust verification systems for autonomous AI agents… |
| `agents-orchestrator` | Agents Orchestrator | Autonomous pipeline manager that orchestrates the entire development workflow. You are the… |
| `aging-parent-care-companion` | Aging Parent Care Companion | Compassionate, HIPAA-aligned care coordination and decision-support agent for family… |
| `automation-governance-architect` | Automation Governance Architect | Governance-first architect for business automations (n8n-first) who audits value, risk,… |
| `business-strategist` | Business Strategist | Senior management consulting specialist for competitive analysis, market entry strategy,… |
| `change-management-consultant` | Change Management Consultant | Expert change management specialist using ADKAR, Kotter, and Prosci frameworks to guide… |
| `chief-financial-officer` | Chief Financial Officer | Strategic finance executive who governs capital allocation, treasury operations, financial… |
| `chief-of-staff` | Chief of Staff | Master coordinator for founders and executives — filters noise, owns processes, enforces… |
| `civil-engineer` | Civil Engineer | Expert civil and structural engineer with global standards coverage — Eurocode, DIN, ACI,… |
| `codebase-archaeologist` | Codebase Archaeologist | Multi-session, multi-tool drift detection specialist who audits codebases touched by… |
| `corporate-training-designer` | Corporate Training Designer | Expert in enterprise training system design and curriculum development — proficient in… |
| `cultural-intelligence-strategist` | Cultural Intelligence Strategist | CQ specialist that detects invisible exclusion, researches global context, and ensures… |
| `customer-service` | Customer Service | Friendly, professional customer service specialist for any industry — handling inquiries,… |
| `customer-success-manager` | Customer Success Manager | Strategic customer success specialist for onboarding, health scoring, QBR facilitation,… |
| `data-consolidation-agent` | Data Consolidation Agent | AI agent that consolidates extracted sales data into live reporting dashboards with… |
| `data-privacy-officer` | Data Privacy Officer | Corporate data privacy specialist and DPO who builds GDPR, CCPA, and global privacy… |
| `developer-advocate` | Developer Advocate | Expert developer advocate specializing in building developer communities, creating… |
| `document-generator` | Document Generator | Expert document creation specialist who generates professional PDF, PPTX, DOCX, and XLSX… |
| `esg-sustainability-officer` | ESG & Sustainability Officer | Corporate sustainability strategist and ESG reporting specialist who builds environmental,… |
| `fedramp-rmf-compliance-engineer` | FedRAMP & RMF Compliance Engineer | Expert FedRAMP and NIST Risk Management Framework compliance engineer specializing in both… |
| `focus-music-architect` | Focus Music Architect | Instrumental focus music specialist and neuroacoustic prompt engineer — crafts high-yield… |
| `french-consulting-market-navigator` | French Consulting Market Navigator | Navigate the French ESN/SI freelance ecosystem — margin models, platform mechanics (Malt,… |
| `government-digital-presales-consultant` | Government Digital Presales Consultant | Presales expert for China's government digital transformation market (ToG), proficient in… |
| `grant-writer` | Grant Writer | Expert grant writing specialist for nonprofits, research institutions, and social… |
| `healthcare-customer-service` | Healthcare Customer Service | Empathetic healthcare customer service specialist for patient support, billing inquiries,… |
| `healthcare-marketing-compliance-specialist` | Healthcare Marketing Compliance Specialist | Expert in healthcare marketing compliance in China, proficient in the Advertising Law,… |
| `hospitality-guest-services` | Hospitality Guest Services | Comprehensive hospitality guest services specialist for hotels, resorts, restaurants, and… |
| `hr-onboarding` | HR Onboarding | Comprehensive HR onboarding specialist for employee orientation, documentation management,… |
| `identity-graph-operator` | Identity Graph Operator | Operates a shared identity graph that multiple AI agents resolve against. Ensures every… |
| `korean-business-navigator` | Korean Business Navigator | Korean business culture for foreign professionals — 품의 decision process, nunchi reading,… |
| `language-translator` | Language Translator | Real-time Spanish ↔ English translation specialist with cultural context, regional dialect… |
| `legal-billing-time-tracking` | Legal Billing & Time Tracking | Comprehensive legal billing and time tracking specialist for accurate time capture,… |
| `legal-client-intake` | Legal Client Intake | Comprehensive legal client intake specialist for qualifying prospects, collecting case… |
| `legal-document-review` | Legal Document Review | Comprehensive legal document review specialist for contracts, litigation documents, and… |
| `loan-officer-assistant` | Loan Officer Assistant | Comprehensive loan officer assistant for mortgage and lending professionals — covering… |
| `lsp-index-engineer` | LSP/Index Engineer | Language Server Protocol specialist building unified code intelligence systems through LSP… |
| `m-a-integration-manager` | M&A Integration Manager | Mergers and acquisitions integration specialist who designs and executes post-merger… |
| `master-plan-architect` | Master Plan Architect | Master planning architect, technical educator, and ruthless plan critic who specializes in… |
| `mcp-builder` | MCP Builder | Expert Model Context Protocol developer who designs, builds, and tests MCP servers that… |
| `medical-billing-coding-specialist` | Medical Billing & Coding Specialist | Expert medical billing and coding specialist for ICD-10-CM/PCS, CPT, and HCPCS coding,… |
| `model-qa-specialist` | Model QA Specialist | Independent model QA expert who audits ML and statistical models end-to-end - from… |
| `operations-manager` | Operations Manager | Business operations specialist who applies Lean, Six Sigma, and systems thinking to… |
| `organizational-psychologist` | Organizational Psychologist | Applied organizational psychologist who diagnoses team dynamics, psychological safety,… |
| `personal-growth-mentor` | Personal Growth Mentor | Cross-domain personal development mentor for goal clarity, habit design, strategic… |
| `pricing-analyst` | Pricing Analyst | Specialized pricing analyst who develops optimal pricing models through market research,… |
| `real-estate-buyer-seller` | Real Estate Buyer & Seller | Comprehensive real estate agent assistant for buyer representation, seller representation,… |
| `recruitment-specialist` | Recruitment Specialist | Expert recruitment operations and talent acquisition specialist — skilled in China's major… |
| `report-distribution-agent` | Report Distribution Agent | AI agent that automates distribution of consolidated sales reports to representatives… |
| `resume-tailor` | Resume Tailor | Candidate-side resume optimization specialist who analyzes job descriptions, maps real… |
| `retail-customer-returns` | Retail Customer Returns | Comprehensive retail customer returns specialist for processing returns, exchanges, and… |
| `sales-data-extraction-agent` | Sales Data Extraction Agent | AI agent specialized in monitoring Excel files and extracting key sales metrics (MTD, YTD,… |
| `sales-outreach` | Sales Outreach | Consultative B2B sales outreach specialist for cold prospecting, lead follow-up, objection… |
| `salesforce-architect` | Salesforce Architect | Solution architecture for Salesforce platform — multi-cloud design, integration patterns,… |
| `strategy-duel-agent` | Strategy Duel Agent | Conducts live strategy duels using game theory and the 36 Chinese stratagems |
| `study-abroad-advisor` | Study Abroad Advisor | Full-spectrum study abroad planning expert covering the US, UK, Canada, Australia, Europe,… |
| `supply-chain-strategist` | Supply Chain Strategist | Expert supply chain management and procurement strategy specialist — skilled in supplier… |
| `workflow-architect` | Workflow Architect | Workflow design specialist who maps complete workflow trees for every system, user… |
| `zk-steward` | ZK Steward | Knowledge-base steward in the spirit of Niklas Luhmann's Zettelkasten. Default… |

### Marketing（`marketing`，36 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `aeo-foundations-architect` | AEO Foundations Architect | Expert in AI Engine Optimization infrastructure — implements llms.txt, AI-aware… |
| `agentic-search-optimizer` | Agentic Search Optimizer | Expert in WebMCP readiness and agentic task completion — audits whether AI agents can… |
| `ai-citation-strategist` | AI Citation Strategist | Expert in AI recommendation engine optimization (AEO/GEO) — audits brand visibility across… |
| `app-store-optimizer` | App Store Optimizer | Expert app store marketing specialist focused on App Store Optimization (ASO), conversion… |
| `baidu-seo-specialist` | Baidu SEO Specialist | Expert Baidu search optimization specialist focused on Chinese search engine ranking,… |
| `bilibili-content-strategist` | Bilibili Content Strategist | Expert Bilibili marketing specialist focused on UP主 growth, danmaku culture mastery, B站… |
| `book-co-author` | Book Co-Author | Strategic thought-leadership book collaborator for founders, experts, and operators… |
| `carousel-growth-engine` | Carousel Growth Engine | Autonomous TikTok and Instagram carousel generation specialist. Analyzes any website URL… |
| `china-e-commerce-operator` | China E-Commerce Operator | Expert China e-commerce operations specialist covering Taobao, Tmall, Pinduoduo, and JD… |
| `china-market-localization-strategist` | China Market Localization Strategist | Full-stack China market localization expert who transforms real-time trend signals into… |
| `content-creator` | Content Creator | Expert content strategist and creator for multi-platform campaigns. Develops editorial… |
| `cross-border-e-commerce-specialist` | Cross-Border E-Commerce Specialist | Full-funnel cross-border e-commerce strategist covering Amazon, Shopee, Lazada,… |
| `douyin-strategist` | Douyin Strategist | Short-video marketing expert specializing in the Douyin platform, with deep expertise in… |
| `email-marketing-strategist` | Email Marketing Strategist | Expert email marketing strategist for CRM-driven campaigns, lifecycle automation,… |
| `global-podcast-strategist` | Global Podcast Strategist | Expert podcast growth specialist focused on show positioning, audience development,… |
| `growth-hacker` | Growth Hacker | Expert growth strategist specializing in rapid user acquisition through data-driven… |
| `instagram-curator` | Instagram Curator | Expert Instagram marketing specialist focused on visual storytelling, community building,… |
| `kuaishou-strategist` | Kuaishou Strategist | Expert Kuaishou marketing strategist specializing in short-video content for China's… |
| `linkedin-content-creator` | LinkedIn Content Creator | Expert LinkedIn content strategist focused on thought leadership, personal brand building,… |
| `livestream-commerce-coach` | Livestream Commerce Coach | Veteran livestream e-commerce coach specializing in host training and live room operations… |
| `multi-platform-publisher` | Multi-Platform Publisher | Expert orchestrator for one-click Chinese blog publishing. Routes a single article to 知乎 /… |
| `podcast-strategist` | Podcast Strategist | Content strategy and operations expert for the Chinese podcast market, with deep expertise… |
| `pr-communications-manager` | PR & Communications Manager | Strategic public relations and communications specialist for media relations, press… |
| `private-domain-operator` | Private Domain Operator | Expert in building enterprise WeChat (WeCom) private domain ecosystems, with deep… |
| `reddit-community-builder` | Reddit Community Builder | Expert Reddit marketing specialist focused on authentic community engagement, value-driven… |
| `seo-specialist` | SEO Specialist | Expert search engine optimization strategist specializing in technical SEO, content… |
| `short-video-editing-coach` | Short-Video Editing Coach | Hands-on short-video editing coach covering the full post-production pipeline, with… |
| `social-media-strategist` | Social Media Strategist | Expert social media strategist for LinkedIn, Twitter, and professional platforms. Creates… |
| `tiktok-strategist` | TikTok Strategist | Expert TikTok marketing specialist focused on viral content creation, algorithm… |
| `twitter-engager` | Twitter Engager | Expert Twitter marketing specialist focused on real-time engagement, thought leadership… |
| `video-optimization-specialist` | Video Optimization Specialist | Video marketing strategist specializing in YouTube algorithm optimization, audience… |
| `wechat-official-account-manager` | WeChat Official Account Manager | Expert WeChat Official Account (OA) strategist specializing in content marketing,… |
| `weibo-strategist` | Weibo Strategist | Full-spectrum operations expert for Sina Weibo, with deep expertise in trending topic… |
| `x-twitter-intelligence-analyst` | X/Twitter Intelligence Analyst | Social intelligence specialist for X/Twitter research, trend detection, account… |
| `xiaohongshu-specialist` | Xiaohongshu Specialist | Expert Xiaohongshu marketing specialist focused on lifestyle content, trend-driven… |
| `zhihu-strategist` | Zhihu Strategist | Expert Zhihu marketing specialist focused on thought leadership, community credibility,… |

### Game Development（`game-development`，21 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `blender-add-on-engineer` | Blender Add-on Engineer | Blender tooling specialist - Builds Python add-ons, asset validators, exporters, and… |
| `economy-designer` | Economy Designer | Virtual economy architect - Masters currency systems, sources and sinks, monetization… |
| `game-audio-engineer` | Game Audio Engineer | Interactive audio specialist - Masters FMOD/Wwise integration, adaptive music systems,… |
| `game-designer` | Game Designer | Systems and mechanics architect - Masters GDD authorship, player psychology, economy… |
| `godot-gameplay-scripter` | Godot Gameplay Scripter | Composition and signal integrity specialist - Masters GDScript 2.0, C# integration,… |
| `godot-multiplayer-engineer` | Godot Multiplayer Engineer | Godot 4 networking specialist - Masters the MultiplayerAPI, scene replication, ENet/WebRTC… |
| `godot-shader-developer` | Godot Shader Developer | Godot 4 visual effects specialist - Masters the Godot Shading Language (GLSL-like),… |
| `level-designer` | Level Designer | Spatial storytelling and flow specialist - Masters layout theory, pacing architecture,… |
| `narrative-designer` | Narrative Designer | Story systems and dialogue architect - Masters GDD-aligned narrative design, branching… |
| `roblox-avatar-creator` | Roblox Avatar Creator | Roblox UGC and avatar pipeline specialist - Masters Roblox's avatar system, UGC item… |
| `roblox-experience-designer` | Roblox Experience Designer | Roblox platform UX and monetization specialist - Masters engagement loop design,… |
| `roblox-systems-scripter` | Roblox Systems Scripter | Roblox platform engineering specialist - Masters Luau, the client-server security model,… |
| `technical-artist` | Technical Artist | Art-to-engine pipeline specialist - Masters shaders, VFX systems, LOD pipelines,… |
| `unity-architect` | Unity Architect | Data-driven modularity specialist - Masters ScriptableObjects, decoupled systems, and… |
| `unity-editor-tool-developer` | Unity Editor Tool Developer | Unity editor automation specialist - Masters custom EditorWindows, PropertyDrawers,… |
| `unity-multiplayer-engineer` | Unity Multiplayer Engineer | Networked gameplay specialist - Masters Netcode for GameObjects, Unity Gaming Services… |
| `unity-shader-graph-artist` | Unity Shader Graph Artist | Visual effects and material specialist - Masters Unity Shader Graph, HLSL, URP/HDRP… |
| `unreal-multiplayer-architect` | Unreal Multiplayer Architect | Unreal Engine networking specialist - Masters Actor replication, GameMode/GameState… |
| `unreal-systems-engineer` | Unreal Systems Engineer | Performance and hybrid architecture specialist - Masters C++/Blueprint continuum, Nanite… |
| `unreal-technical-artist` | Unreal Technical Artist | Unreal Engine visual pipeline specialist - Masters the Material Editor, Niagara VFX,… |
| `unreal-world-builder` | Unreal World Builder | Open-world and environment specialist - Masters UE5 World Partition, Landscape, procedural… |

### GIS（`gis`，13 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `3d-scene-developer` | 3D & Scene Developer | Web 3D visualization specialist who creates immersive 3D scenes, terrain models, point… |
| `bim-gis-specialist` | BIM/GIS Specialist | Integration specialist who bridges Building Information Modeling and Geographic… |
| `cartography-designer` | Cartography Designer | Map aesthetics specialist who designs beautiful, readable, and effective maps — color… |
| `drone-reality-mapping-specialist` | Drone/Reality Mapping Specialist | Photogrammetry and reality capture expert who processes drone imagery into orthomosaics,… |
| `geoai-ml-engineer` | GeoAI/ML Engineer | Geospatial machine learning specialist who builds models for feature extraction, object… |
| `geoprocessing-specialist` | Geoprocessing Specialist | ArcPy and Python toolbox expert who automates spatial workflows — builds .pyt toolboxes,… |
| `gis-analyst` | GIS Analyst | Day-to-day GIS operator who creates maps, manages layers, performs spatial queries, and… |
| `gis-qa-engineer` | GIS QA Engineer | Quality assurance specialist who validates geospatial data integrity — topology checks,… |
| `solution-engineer` | Solution Engineer | Hands-on GIS prototype builder who takes strategy from Technical Consultant and turns it… |
| `spatial-data-engineer` | Spatial Data Engineer | ETL specialist who transforms messy geospatial data from any source into clean,… |
| `spatial-data-scientist` | Spatial Data Scientist | Advanced spatial analytics specialist who applies statistical modeling, spatial… |
| `technical-consultant` | Technical Consultant | Strategic GIS advisor who translates business problems into geospatial solutions — gap… |
| `web-gis-developer` | Web GIS Developer | Full-stack web GIS engineer who builds interactive mapping applications — MapLibre GL JS,… |

### Security（`security`，12 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `ai-generated-code-security-auditor` | AI-Generated Code Security Auditor | Security reviewer for AI-generated and vibe-coded apps — hunts the hardcoded secrets,… |
| `application-security-engineer` | Application Security Engineer | AppSec specialist who secures the software development lifecycle through threat modeling,… |
| `blockchain-security-auditor` | Blockchain Security Auditor | Expert smart contract security auditor specializing in vulnerability detection, formal… |
| `cloud-security-architect` | Cloud Security Architect | Cloud-native security specialist designing zero trust architectures, implementing… |
| `compliance-auditor` | Compliance Auditor | Expert technical compliance auditor specializing in SOC 2, ISO 27001, HIPAA, and PCI-DSS… |
| `incident-responder` | Incident Responder | Digital forensics and incident response specialist who leads breach investigations,… |
| `penetration-tester` | Penetration Tester | Offensive security specialist conducting authorized penetration tests, red team… |
| `secrets-credential-hygiene-engineer` | Secrets & Credential Hygiene Engineer | Owns the full lifecycle of secrets and credentials — detection, prevention, vaulting,… |
| `security-architect` | Security Architect | Expert security architect specializing in threat modeling, secure-by-design architecture,… |
| `senior-secops-engineer` | Senior SecOps Engineer | Defensive application security specialist who scans every code submission for secrets and… |
| `threat-detection-engineer` | Threat Detection Engineer | Expert detection engineer specializing in SIEM rule development, MITRE ATT&CK coverage… |
| `threat-intelligence-analyst` | Threat Intelligence Analyst | Cyber threat intelligence specialist who tracks adversary groups, maps attack campaigns to… |

### Design（`design`，10 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `brand-guardian` | Brand Guardian | Expert brand strategist and guardian specializing in brand identity development,… |
| `image-prompt-engineer` | Image Prompt Engineer | Expert photography prompt engineer specializing in crafting detailed, evocative prompts… |
| `inclusive-visuals-specialist` | Inclusive Visuals Specialist | Representation expert who defeats systemic AI biases to generate culturally accurate,… |
| `persona-walkthrough-specialist` | Persona Walkthrough Specialist | Simulate cognitive walkthroughs of web pages from a defined persona's psychological… |
| `ui-designer` | UI Designer | Expert UI designer specializing in visual design systems, component libraries, and… |
| `ui-finish-gate-reviewer` | UI Finish-Gate Reviewer | Product-interface reviewer who catches generic, interchangeable UI before it ships by… |
| `ux-architect` | UX Architect | Technical architecture and UX specialist who provides developers with solid foundations,… |
| `ux-researcher` | UX Researcher | Expert user experience researcher specializing in user behavior analysis, usability… |
| `visual-storyteller` | Visual Storyteller | Expert visual communication specialist focused on creating compelling visual narratives,… |
| `whimsy-injector` | Whimsy Injector | Expert creative specialist focused on adding personality, delight, and playful elements to… |

### Sales（`sales`，9 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `account-strategist` | Account Strategist | Expert post-sale account strategist specializing in land-and-expand execution, stakeholder… |
| `deal-strategist` | Deal Strategist | Senior deal strategist specializing in MEDDPICC qualification, competitive positioning,… |
| `discovery-coach` | Discovery Coach | Coaches sales teams on elite discovery methodology — question design, current-state… |
| `offer-lead-gen-strategist` | Offer & Lead Gen Strategist | Top-of-funnel architect who designs irresistible offers and lead magnets that attract… |
| `outbound-strategist` | Outbound Strategist | Signal-based outbound specialist who designs multi-channel prospecting sequences, defines… |
| `pipeline-analyst` | Pipeline Analyst | Revenue operations analyst specializing in pipeline health diagnostics, deal velocity… |
| `proposal-strategist` | Proposal Strategist | Strategic proposal architect who transforms RFPs and sales opportunities into compelling… |
| `sales-coach` | Sales Coach | Expert sales coaching specialist focused on rep development, pipeline review facilitation,… |
| `sales-engineer` | Sales Engineer | Senior pre-sales engineer specializing in technical discovery, demo engineering, POC… |

### Testing（`testing`，9 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `accessibility-auditor` | Accessibility Auditor | Expert accessibility specialist who audits interfaces against WCAG standards, tests with… |
| `api-tester` | API Tester | Expert API testing specialist focused on comprehensive API validation, performance… |
| `evidence-collector` | Evidence Collector | Screenshot-obsessed, fantasy-allergic QA specialist - Default to finding 3-5 issues,… |
| `performance-benchmarker` | Performance Benchmarker | Expert performance testing and optimization specialist focused on measuring, analyzing,… |
| `reality-checker` | Reality Checker | Stops fantasy approvals, evidence-based certification - Default to "NEEDS WORK", requires… |
| `test-automation-engineer` | Test Automation Engineer | Expert end-to-end test automation engineer for Playwright and Cypress — resilient… |
| `test-results-analyzer` | Test Results Analyzer | Expert test analysis specialist focused on comprehensive test result evaluation, quality… |
| `tool-evaluator` | Tool Evaluator | Expert technology assessment specialist focused on evaluating, testing, and recommending… |
| `workflow-optimizer` | Workflow Optimizer | Expert process improvement specialist focused on analyzing, optimizing, and automating… |

### Paid Media（`paid-media`，7 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `ad-creative-strategist` | Ad Creative Strategist | Paid media creative specialist focused on ad copywriting, RSA optimization, asset group… |
| `paid-media-auditor` | Paid Media Auditor | Comprehensive paid media auditor who systematically evaluates Google Ads, Microsoft Ads,… |
| `paid-social-strategist` | Paid Social Strategist | Cross-platform paid social advertising specialist covering Meta (Facebook/Instagram),… |
| `ppc-campaign-strategist` | PPC Campaign Strategist | Senior paid media strategist specializing in large-scale search, shopping, and performance… |
| `programmatic-display-buyer` | Programmatic & Display Buyer | Display advertising and programmatic media buying specialist covering managed placements,… |
| `search-query-analyst` | Search Query Analyst | Specialist in search term analysis, negative keyword architecture, and query-to-intent… |
| `tracking-measurement-specialist` | Tracking & Measurement Specialist | Expert in conversion tracking architecture, tag management, and attribution modeling… |

### Project Management（`project-management`，7 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `experiment-tracker` | Experiment Tracker | Expert project manager specializing in experiment design, execution tracking, and… |
| `jira-workflow-steward` | Jira Workflow Steward | Expert delivery operations specialist who enforces Jira-linked Git workflows, traceable… |
| `meeting-notes-specialist` | Meeting Notes Specialist | Extract structured decisions, action items, and open questions from meeting transcripts or… |
| `project-shepherd` | Project Shepherd | Expert project manager specializing in cross-functional project coordination, timeline… |
| `senior-project-manager` | Senior Project Manager | Converts specs to tasks and remembers previous projects. Focused on realistic scope, no… |
| `studio-operations` | Studio Operations | Expert operations manager specializing in day-to-day studio efficiency, process… |
| `studio-producer` | Studio Producer | Senior strategic leader specializing in high-level creative and technical project… |

### Academic（`academic`，6 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `anthropologist` | Anthropologist | Expert in cultural systems, rituals, kinship, belief systems, and ethnographic method —… |
| `geographer` | Geographer | Expert in physical and human geography, climate systems, cartography, and spatial analysis… |
| `historian` | Historian | Expert in historical analysis, periodization, material culture, and historiography —… |
| `narratologist` | Narratologist | Expert in narrative theory, story structure, character arcs, and literary analysis —… |
| `psychologist` | Psychologist | Expert in human behavior, personality theory, motivation, and cognitive patterns — builds… |
| `statistician` | Statistician | Expert in quantitative research methodology, experimental design, and statistical… |

### Spatial Computing（`spatial-computing`，6 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `macos-spatial-metal-engineer` | macOS Spatial/Metal Engineer | Native Swift and Metal specialist building high-performance 3D rendering systems and… |
| `terminal-integration-specialist` | Terminal Integration Specialist | Terminal emulation, text rendering optimization, and SwiftTerm integration for modern… |
| `visionos-spatial-engineer` | visionOS Spatial Engineer | Native visionOS spatial computing, SwiftUI volumetric interfaces, and Liquid Glass design… |
| `xr-cockpit-interaction-specialist` | XR Cockpit Interaction Specialist | Specialist in designing and developing immersive cockpit-based control systems for XR… |
| `xr-immersive-developer` | XR Immersive Developer | Expert WebXR and immersive technology developer with specialization in browser-based… |
| `xr-interface-architect` | XR Interface Architect | Spatial interaction designer and interface strategist for immersive AR/VR/XR environments |

### Support（`support`，6 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `analytics-reporter` | Analytics Reporter | Expert data analyst transforming raw data into actionable business insights. Creates… |
| `executive-summary-generator` | Executive Summary Generator | Consultant-grade AI specialist trained to think and communicate like a senior strategy… |
| `finance-tracker` | Finance Tracker | Expert financial analyst and controller specializing in financial planning, budget… |
| `infrastructure-maintainer` | Infrastructure Maintainer | Expert infrastructure specialist focused on system reliability, performance optimization,… |
| `legal-compliance-checker` | Legal Compliance Checker | Expert legal and compliance specialist ensuring business operations, data handling, and… |
| `support-responder` | Support Responder | Expert customer support specialist delivering exceptional customer service, issue… |

### Finance（`finance`，5 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `bookkeeper-controller` | Bookkeeper & Controller | Expert bookkeeper and controller specializing in day-to-day accounting operations,… |
| `financial-analyst` | Financial Analyst | Expert financial analyst specializing in financial modeling, forecasting, scenario… |
| `fp-a-analyst` | FP&A Analyst | Expert Financial Planning & Analysis (FP&A) analyst specializing in budgeting, variance… |
| `investment-researcher` | Investment Researcher | Expert investment researcher specializing in market research, due diligence, portfolio… |
| `tax-strategist` | Tax Strategist | Expert tax strategist specializing in tax optimization, multi-jurisdictional compliance,… |

### Product（`product`，5 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `behavioral-nudge-engine` | Behavioral Nudge Engine | Behavioral psychology specialist that adapts software interaction cadences and styles to… |
| `feedback-synthesizer` | Feedback Synthesizer | Expert in collecting, analyzing, and synthesizing user feedback from multiple channels to… |
| `product-manager` | Product Manager | Holistic product leader who owns the full product lifecycle — from discovery and strategy… |
| `sprint-prioritizer` | Sprint Prioritizer | Expert product manager specializing in agile sprint planning, feature prioritization, and… |
| `trend-researcher` | Trend Researcher | Expert market intelligence analyst specializing in identifying emerging trends,… |

### Healthcare（`healthcare`，3 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `clinical-evidence-agent` | Clinical Evidence Agent | Evidence standards and clinical credibility framework for AI agents |
| `healthcare-innovation-strategist` | Healthcare Innovation Strategist | Strategic narrative architect for healthcare founders operating at |
| `sovereign-health-systems-agent` | Sovereign Health Systems Agent | Government health mandate engagement framework for AI agents |

### Research（`research`，1 个）

| slug（读这个文件） | 角色 | 一句话 |
|---|---|---|
| `research-synthesist` | Research Synthesist | Expert in literature review, source evaluation, and evidence synthesis — turns a scattered… |

---

**合计 279 个角色。** 裁剪：删人设目录下不要的 `.md`（OpenCode 版路径 `.opencode/role-pool/`），
再把本文件里对应的表格行一并删掉，避免索引指向不存在的文件。

