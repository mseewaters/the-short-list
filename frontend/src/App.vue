<script setup>
import { computed, onMounted, ref } from "vue";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const sessionId = ref(null);
const input = ref(
  "I need a ceiling fan for an old house bedroom. I care about quiet, low profile, and not ugly.",
);
const messages = ref([]);
const clarifyResult = ref(null);
const searchResult = ref(null);
const stage = ref("understand");
const loading = ref(false);
const searchLoading = ref(false);
const error = ref("");

const requirements = computed(() => clarifyResult.value?.requirements || []);
const missingFields = computed(() => clarifyResult.value?.missing_fields || []);
const agentTrace = computed(() => clarifyResult.value?.agent_trace || []);
const stages = [
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
    throw new Error(`Request failed: ${response.status}`);
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
  stage.value = "understand";
  input.value = "";
  await createSession();
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
    const result = await apiFetch("/clarify", {
      method: "POST",
      body: JSON.stringify({
        session_id: sessionId.value,
        user_id: "default",
        message,
      }),
    });

    clarifyResult.value = result;
    searchResult.value = null;
    messages.value.push({ role: "agent", text: result.agent_message });
  } catch (err) {
    error.value = "I had trouble updating the requirements. Please try again.";
    input.value = message;
  } finally {
    loading.value = false;
  }
}

async function searchNow() {
  if (!sessionId.value || searchLoading.value) {
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

onMounted(async () => {
  try {
    await createSession();
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
      >
        {{ item.label }}
      </span>
      <button type="button" @click="resetSession">Reset session</button>
    </section>

    <section v-if="stage === 'understand'" class="workspace">
      <div class="conversation-panel">
        <header>
          <p class="eyebrow">The Short List</p>
          <h1>Tell me what you need.</h1>
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
            placeholder="Describe the product decision..."
            :disabled="loading || !sessionId"
          />
          <button type="submit" :disabled="loading || !sessionId || !input.trim()">
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
          </div>

          <section>
            <h2>Category</h2>
            <p v-if="clarifyResult?.category" class="category">{{ clarifyResult.category }}</p>
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
          <div v-if="agentTrace.length">
            <p v-for="trace in agentTrace" :key="trace">{{ trace }}</p>
          </div>
          <p v-else class="empty-message">No trace yet.</p>
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
