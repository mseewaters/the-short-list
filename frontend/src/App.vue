<script setup>
import { computed, onMounted, ref } from "vue";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

const sessionId = ref(null);
const input = ref(
  "I need a ceiling fan for an old house bedroom. I care about quiet, low profile, and not ugly.",
);
const messages = ref([]);
const searchIntent = ref(null);
const agentTrace = ref([]);
const loading = ref(false);
const error = ref("");

const requirements = computed(() => searchIntent.value?.requirements || []);
const missingInformation = computed(() => searchIntent.value?.missing_information || []);

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

    searchIntent.value = result.search_intent;
    agentTrace.value = result.activity_events || [];
    messages.value.push({ role: "agent", text: result.agent_message });
  } catch (err) {
    error.value = "I had trouble updating the requirements. Please try again.";
    input.value = message;
  } finally {
    loading.value = false;
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
      <span class="stage active">Understand</span>
      <span class="stage">Confirm</span>
      <span class="stage">Research</span>
      <span class="stage">Results</span>
    </section>

    <section class="workspace">
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
      </div>

      <div class="side-column">
        <aside class="requirements-panel" aria-label="Requirements">
          <div class="panel-header">
            <p class="eyebrow">Requirements</p>
            <strong>{{ requirements.length }}</strong>
          </div>

          <p v-if="searchIntent?.category_label" class="category">
            Category: {{ searchIntent.category_label }}
          </p>

          <div v-if="requirements.length" class="requirements-list">
            <article v-for="requirement in requirements" :key="requirement.id" class="requirement">
              <h2>{{ requirement.label }}</h2>
              <p>{{ requirement.interpreted_need }}</p>
            </article>
          </div>

          <p v-else class="empty-message">Requirements will appear here after you send a message.</p>

          <div v-if="missingInformation.length" class="missing-info">
            <h2>Still Needed</h2>
            <p v-for="item in missingInformation" :key="item.field">{{ item.question }}</p>
          </div>
        </aside>

        <aside class="agent-trace-panel" aria-label="Agent trace">
          <p class="eyebrow">Agent Trace</p>

          <div v-if="agentTrace.length" class="trace-list">
            <article v-for="event in agentTrace" :key="event.node" class="trace-item">
              <h2>{{ event.label }}</h2>
              <p>{{ event.detail }}</p>
            </article>
          </div>

          <p v-else class="empty-message">Trace output will appear after /clarify runs.</p>
        </aside>
      </div>
    </section>
  </main>
</template>
