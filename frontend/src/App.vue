<script setup>
import { computed, onMounted, ref } from "vue";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const sessionId = ref(null);
const input = ref(
  "Describe the product you are looking for in plain language, including any needs, constraints, preferences, or answers to intake questions. For example: 'I need a ceiling fan for my living room. I have a budget of $200, the ceiling is 8 feet high, and I want something quiet with a modern look.'",
);
const messages = ref([]);
const clarifyResult = ref(null);
const searchResult = ref(null);
const stage = ref("category");
const categoryInput = ref("");
const categoryProposal = ref(null);
const calibratedCategory = ref("");
const selectedCategory = ref("");
const loading = ref(false);
const searchLoading = ref(false);
const intelligenceLoading = ref(false);
const categoryExtractLoading = ref(false);
const categoryIntelligence = ref(null);
const llmConfig = ref(null);
const error = ref("");

const requirements = computed(() => clarifyResult.value?.requirements || []);
const missingFields = computed(() => clarifyResult.value?.missing_fields || []);
const agentTrace = computed(() => clarifyResult.value?.agent_trace || []);
const userRequirementProfile = computed(() => clarifyResult.value?.user_requirement_profile || null);
const categorySchema = computed(() => categoryIntelligence.value?.category_schema || null);
const visibleDecisionAttributes = computed(() => categorySchema.value?.decision_attributes?.slice(0, 12) || []);
const visibleSearchGateAttributes = computed(() => visibleDecisionAttributes.value.filter((a) => a.search_gate));
const visibleEntityTerms = computed(() => categorySchema.value?.entity_terms?.slice(0, 8) || []);
const visibleRisks = computed(() => categorySchema.value?.risks?.slice(0, 5) || []);
const requirementScoringPreview = computed(() => {
  const profile = userRequirementProfile.value;
  const attributes = categorySchema.value?.decision_attributes || [];
  const attributeByName = new Map(
    attributes.map((attribute) => [attribute.name?.toLowerCase(), attribute]),
  );

  if (!profile?.requirements?.length) {
    return null;
  }

  return {
    categoryName: profile.categoryName,
    readyToResearch: Boolean(clarifyResult.value?.ready_to_search),
    scoringInputs: profile.requirements.map((requirement) => {
      const attribute = attributeByName.get(requirement.attributeName?.toLowerCase()) || {};
      return {
        attributeName: requirement.attributeName,
        requirementStatus: requirement.status,
        userValue: requirement.value,
        userImportance: requirement.importance,
        source: requirement.source,
        confidence: requirement.confidence,
        normalizedOperator: requirement.normalizedOperator,
        normalizedValue: requirement.normalizedValue,
        unit: requirement.unit || attribute.unit || null,
        hardness: requirement.hardness,
        weight: requirement.weight,
        productEvidenceConfidence: requirement.productEvidenceConfidence,
        missingProductDataStrategy: requirement.missingProductDataStrategy,
        scoringFunction: requirement.scoringFunction,
        needsMoreSpecification: requirement.needsMoreSpecification,
        specificationQuestion: requirement.specificationQuestion,
        evidence: requirement.evidence,
        productAttributeExpected: attribute.name || requirement.attributeName,
        productValueType: attribute.value_type || "unknown",
        scoreDirection: attribute.score_direction || "match_preference",
        searchGate: Boolean(attribute.search_gate),
        typicalValues: attribute.typical_values || null,
        scoringUse: scoringUseFor(requirement, attribute),
      };
    }),
  };
});
const requirementScoringPreviewJson = computed(() => (
  requirementScoringPreview.value
    ? JSON.stringify(requirementScoringPreview.value, null, 2)
    : ""
));
const stages = [
  { key: "category", label: "Category" },
  { key: "understand", label: "Understand" },
  { key: "research", label: "Research" },
  { key: "results", label: "Your Short List" },
];

async function apiFetch(path, options = {}) {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.text();
    const error = new Error(`Request failed: ${response.status} ${detail}`);
    error.status = response.status;
    error.detail = detail;
    throw error;
  }

  return response.json();
}

async function createSession() {
  error.value = "";
  const session = await apiFetch("/sessions", {
    method: "POST",
    body: JSON.stringify({ user_id: "default" }),
  });

  sessionId.value = session.session_id;
}

async function resetSession() {
  messages.value = [];
  clarifyResult.value = null;
  searchResult.value = null;
  categoryIntelligence.value = null;
  categoryProposal.value = null;
  calibratedCategory.value = "";
  selectedCategory.value = "";
  categoryInput.value = "";
  stage.value = "category";
  input.value = "";
  await createSession();
}

async function resetRequirements() {
  if (!sessionId.value || loading.value) {
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    await apiFetch(`/sessions/${sessionId.value}/reset-requirements`, { method: "POST" });
    messages.value = [];
    clarifyResult.value = null;
    searchResult.value = null;
    input.value = "";
  } catch (err) {
    error.value = `Could not reset requirements. ${err.message}`;
  } finally {
    loading.value = false;
  }
}

function clearDownstreamState() {
  messages.value = [];
  clarifyResult.value = null;
  searchResult.value = null;
  input.value = "";
}

async function sendMessage() {
  const message = input.value.trim();
  if (!message || !sessionId.value || loading.value) {
    return;
  }

  loading.value = true;
  error.value = "";
  messages.value.push({ role: "user", text: message });
  input.value = "";

  try {
    const result = await submitClarify(message);
    clarifyResult.value = result;
    searchResult.value = null;
    messages.value.push({ role: "agent", text: result.agent_message });
  } catch (err) {
    error.value = `I had trouble updating the requirements. ${err.message}`;
    input.value = message;
  } finally {
    loading.value = false;
  }
}

async function submitClarify(message, retried = false) {
  try {
    return await apiFetch("/clarify", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId.value,
        user_id: "default",
        message,
        category: selectedCategory.value,
        category_context: categorySchema.value,
      }),
    });
  } catch (err) {
    if (!retried && err.status === 404 && err.detail.includes("Session not found")) {
      await createSession();
      return submitClarify(message, true);
    }

    throw err;
  }
}

async function searchNow() {
  if (!sessionId.value || searchLoading.value || !categoryIntelligence.value) {
    return;
  }

  searchLoading.value = true;
  error.value = "";

  try {
    stage.value = "research";
    searchResult.value = await apiFetch("/search", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId.value,
      }),
    });
    stage.value = "results";
  } catch (err) {
    stage.value = "understand";
    error.value = "I had trouble running the mock search. Please try again.";
  } finally {
    searchLoading.value = false;
  }
}

async function loadCategoryIntelligence() {
  const category = calibratedCategory.value || categoryProposal.value?.proposed_category;
  if (!category || intelligenceLoading.value) {
    return;
  }

  intelligenceLoading.value = true;
  error.value = "";
  clearDownstreamState();
  selectedCategory.value = category;

  try {
    categoryIntelligence.value = await apiFetch("/api/category-intelligence", {
      method: "POST",
      body: JSON.stringify({
        category,
        context: "",
      }),
    });
    stage.value = "understand";
  } catch (err) {
    error.value = "I had trouble loading category intelligence.";
  } finally {
    intelligenceLoading.value = false;
  }
}

async function extractCategory() {
  const userInput = categoryInput.value.trim();
  if (!userInput || categoryExtractLoading.value) {
    return;
  }

  categoryExtractLoading.value = true;
  error.value = "";
  categoryProposal.value = null;
  categoryIntelligence.value = null;
  selectedCategory.value = "";
  clearDownstreamState();

  try {
    categoryProposal.value = await apiFetch("/api/category-extract", {
      method: "POST",
      body: JSON.stringify({
        user_input: userInput,
        additional_context: null,
      }),
    });
    calibratedCategory.value = categoryProposal.value.proposed_category;
  } catch (err) {
    error.value = "I had trouble extracting the category.";
  } finally {
    categoryExtractLoading.value = false;
  }
}

function changeCategoryInput() {
  categoryProposal.value = null;
  calibratedCategory.value = "";
}

async function loadLlmConfig() {
  try {
    llmConfig.value = await apiFetch("/api/llm-config");
  } catch (err) {
    llmConfig.value = {
      provider: "unknown",
      model: "unknown",
    };
  }
}

function scoringUseFor(requirement, attribute) {
  if (requirement.scoringFunction) {
    return requirement.scoringFunction;
  }
  if (requirement.status === "ignored") {
    return "do_not_score";
  }
  if (requirement.status === "conflicted") {
    return "needs_resolution_before_scoring";
  }
  if (attribute.score_direction === "must_have" || attribute.search_gate) {
    return "filter_or_heavy_penalty_if_unmet";
  }
  if (attribute.score_direction === "lower_is_better") {
    return "score_lower_product_value_better_against_user_limit_or_preference";
  }
  if (attribute.score_direction === "higher_is_better") {
    return "score_higher_product_value_better_against_user_threshold_or_preference";
  }
  return "score_match_to_user_preference";
}

function canOpenStage(stageKey) {
  if (stageKey === "category") {
    return true;
  }
  if (stageKey === "understand") {
    return Boolean(categoryIntelligence.value);
  }
  if (stageKey === "research") {
    return Boolean(categoryIntelligence.value && clarifyResult.value?.ready_to_search);
  }
  if (stageKey === "results") {
    return Boolean(searchResult.value);
  }
  return false;
}

function openStage(stageKey) {
  if (canOpenStage(stageKey)) {
    stage.value = stageKey;
  }
}

onMounted(async () => {
  try {
    await createSession();
    await loadLlmConfig();
  } catch (err) {
    error.value = "Could not create a session. Make sure the backend is running.";
  }
});
</script>

<template>
  <main class="app-shell">
    <section class="stage-bar" aria-label="Workflow stage">
      <span
        v-for="item in stages"
        :key="item.key"
        class="stage"
        :class="{ active: stage === item.key }"
        @click="openStage(item.key)"
      >
        {{ item.label }}
      </span>
      <button type="button" @click="resetSession">Reset session</button>
    </section>

    <section v-if="stage === 'category'" class="report-layout">
      <section class="requirements-panel">
        <p class="eyebrow">Category</p>
        <h1>What type of product are you looking to buy?</h1>

        <form class="composer" @submit.prevent="extractCategory">
          <textarea
            v-model="categoryInput"
            rows="2"
            placeholder="Describe the product you are looking for in plain language..."
            :disabled="categoryExtractLoading || intelligenceLoading"
          />
          <button type="submit" :disabled="categoryExtractLoading || intelligenceLoading || !categoryInput.trim()">
            {{ categoryExtractLoading ? "Extracting category..." : "Extract category" }}
          </button>
        </form>

        <p v-if="error" class="error">{{ error }}</p>

        <section v-if="categoryProposal" class="results-panel">
          <h2>Select the desired category:</h2>
          <p>Key: {{ categoryProposal.normalized_category_key }}</p>
          <p>Confidence: {{ categoryProposal.confidence }}</p>
          <p>Matched existing category: {{ categoryProposal.matched_existing_category ? "yes" : "no" }}</p>
          <p>{{ categoryProposal.explanation }}</p>

          <section>
            <h3>What we think you are looking for</h3>
            <label>
              <input
                v-model="calibratedCategory"
                type="radio"
                :value="categoryProposal.proposed_category"
              />
              {{ categoryProposal.proposed_category }}
            </label>
          </section>

          <section>
            <h3>Broader</h3>
            <label>
              <input
                v-model="calibratedCategory"
                type="radio"
                :value="categoryProposal.broader_category"
              />
              {{ categoryProposal.broader_category }}
            </label>
          </section>

          <section>
            <h3>More specific</h3>
            <label v-for="category in categoryProposal.more_specific_categories" :key="category">
              <input v-model="calibratedCategory" type="radio" :value="category" />
              {{ category }}
            </label>
          </section>

          <button type="button" :disabled="intelligenceLoading" @click="loadCategoryIntelligence">
            {{ intelligenceLoading ? "Loading category intelligence..." : "Confirm this choice" }}
          </button>
          <button type="button" :disabled="intelligenceLoading" @click="changeCategoryInput">
            Change request
          </button>
        </section>

        <section v-if="categoryIntelligence" class="results-panel">
          <h2>{{ selectedCategory }}</h2>

          <h3>Category Summary</h3>
          <p>{{ categorySchema?.summary }}</p>

          <h3>Must Resolve Before Search</h3>
          <ul>
            <li v-for="attribute in visibleSearchGateAttributes" :key="attribute.key">
              <strong>{{ attribute.name }}</strong> — {{ attribute.clarifying_question }}
            </li>
          </ul>

          <h3>Decision Attributes</h3>
          <ul>
            <li v-for="attribute in visibleDecisionAttributes" :key="attribute.key">
              {{ attribute.name }}
              ({{ attribute.value_type }}{{ attribute.unit ? ', ' + attribute.unit : '' }},
              {{ attribute.score_direction }})
              <span v-if="attribute.search_gate"> 🔑</span>
            </li>
          </ul>

          <h3>Common Product Terms</h3>
          <ul>
            <li v-for="term in visibleEntityTerms" :key="term">{{ term }}</li>
          </ul>

          <h3>Risks / Gotchas</h3>
          <ul>
            <li v-for="risk in visibleRisks" :key="risk">{{ risk }}</li>
          </ul>

          <button type="button" @click="stage = 'understand'">Continue to Understand</button>
        </section>
      </section>
    </section>

    <section v-else-if="stage === 'understand'" class="workspace">
      <div class="conversation-panel">
        <header>
          <p class="eyebrow">The Short List</p>
          <h2>Tell me about what you are looking for in {{ selectedCategory }}</h2>
          <p v-if="selectedCategory">
            {{ categorySchema?.decision_attributes?.length || 0 }} decision attributes loaded.
          </p>
        </header>

        <div class="messages" aria-live="polite">
          <p v-if="messages.length === 0" class="empty-message">
            Start with a plain-English product request.
          </p>

          <article
            v-for="(message, index) in messages"
            :key="`${message.role}-${index}`"
            class="message"
            :class="message.role"
          >
            {{ message.text }}
          </article>
        </div>

        <form class="composer" @submit.prevent="sendMessage">
          <textarea
            v-model="input"
            rows="4"
            placeholder="Describe your needs, constraints, preferences, or answers to intake questions..."
            :disabled="loading || !sessionId || !categoryIntelligence"
          />
          <button type="submit" :disabled="loading || !sessionId || !input.trim() || !categoryIntelligence">
            {{ loading ? "Sending..." : "Send" }}
          </button>
        </form>

        <p v-if="error" class="error">{{ error }}</p>

        <button
          v-if="clarifyResult?.ready_to_search"
          type="button"
          :disabled="searchLoading"
          @click="searchNow"
        >
          {{ searchLoading ? "Searching..." : "Looks right — search now" }}
        </button>

      </div>

      <div class="side-column">
        <aside class="requirements-panel" aria-label="Requirements">
          <div class="panel-header">
            <p class="eyebrow">Requirements</p>
            <strong>{{ requirements.length }}</strong>
            <button
              v-if="clarifyResult"
              type="button"
              class="reset-requirements-btn"
              :disabled="loading"
              @click="resetRequirements"
            >
              Reset
            </button>
          </div>

          <section>
            <h2>Category</h2>
            <p v-if="selectedCategory" class="category">{{ selectedCategory }}</p>
            <p v-else class="empty-message">No category yet.</p>
          </section>

          <section>
            <h2>Requirements</h2>
            <div v-if="requirements.length" class="requirements-list">
              <article
                v-for="requirement in requirements"
                :key="`${requirement.label}-${requirement.value}`"
                class="requirement"
              >
                <h3>{{ requirement.label }}</h3>
                <p>{{ requirement.value }}</p>
              </article>
            </div>
            <p v-else class="empty-message">No requirements yet.</p>
          </section>

          <section>
            <h2>Missing Information</h2>
            <div v-if="missingFields.length" class="missing-info">
              <p v-for="field in missingFields" :key="field">{{ field }}</p>
            </div>
            <p v-else class="empty-message">No missing information.</p>
          </section>
        </aside>

        <aside class="requirements-panel" aria-label="Agent trace">
          <p class="eyebrow">Agent Trace</p>
          <section>
            <h2>LLM</h2>
            <p>Provider: {{ llmConfig?.provider || "loading" }}</p>
            <p>Model: {{ llmConfig?.model || "loading" }}</p>
          </section>
          <div v-if="agentTrace.length">
            <p v-for="trace in agentTrace" :key="trace">{{ trace }}</p>
          </div>
          <p v-else class="empty-message">No trace yet.</p>

          <section v-if="requirementScoringPreview">
            <h2>User Attribute Scoring JSON</h2>
            <pre class="trace-json">{{ requirementScoringPreviewJson }}</pre>
          </section>
        </aside>
      </div>
    </section>

    <section v-else-if="stage === 'research'" class="report-layout">
      <section class="requirements-panel">
        <p class="eyebrow">Research</p>
        <h1>Mock search is running.</h1>
        <p>Using the current requirements to score hardcoded ceiling fan candidates.</p>

        <h2>Agent Trace</h2>
        <p v-for="trace in agentTrace" :key="trace">{{ trace }}</p>
      </section>
    </section>

    <section v-else class="report-layout">
      <section class="requirements-panel recommendation-panel">
        <p class="eyebrow">Recommendation</p>
        <h1>Here is what I recommend and why.</h1>
        <p>{{ searchResult.recommendation }}</p>
      </section>

      <section class="results-panel">
        <h2>Your Short List</h2>
        <article
          v-for="candidate in searchResult.candidates"
          :key="candidate.id"
          class="requirements-panel product-card"
        >
          <h3>{{ candidate.name }}</h3>
          <p>{{ candidate.price }} · Score: {{ candidate.score }} · {{ candidate.verdict }}</p>

          <div>
            <p v-for="criterion in candidate.criteria" :key="criterion.label">
              {{ criterion.met ? "Met" : "Not met" }} — {{ criterion.label }}:
              {{ criterion.note }}
            </p>
          </div>
        </article>
      </section>
    </section>
  </main>
</template>
