const state = {
  selectedTeamId: null,
  teams: [],
};

const teamListEl = document.getElementById("teamList");
const teamListTemplate = document.getElementById("teamListItemTemplate");
const memberListEl = document.getElementById("memberList");
const memberTemplate = document.getElementById("memberListItemTemplate");
const teamDetailsPanel = document.getElementById("teamDetailsPanel");
const emptyState = document.getElementById("emptyState");
const teamDetailsTitle = document.getElementById("teamDetailsTitle");
const memberCountEl = document.getElementById("memberCount");
const toastEl = document.getElementById("toast");

const createTeamForm = document.getElementById("createTeamForm");
const updateTeamForm = document.getElementById("updateTeamForm");
const addMemberForm = document.getElementById("addMemberForm");
const deleteTeamButton = document.getElementById("deleteTeamButton");
const refreshTeamsButton = document.getElementById("refreshTeams");

const formatDate = (value) => {
  const date = new Date(value);
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
};

const showToast = (message, type = "info") => {
  toastEl.textContent = message;
  toastEl.dataset.type = type;
  toastEl.classList.add("show");
  window.setTimeout(() => toastEl.classList.remove("show"), 3000);
};

const handleResponse = async (response) => {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ error: "Request failed" }));
    throw new Error(payload.error || "Request failed");
  }
  return response.json();
};

const renderTeamList = () => {
  teamListEl.innerHTML = "";

  if (!state.teams.length) {
    const emptyEl = document.createElement("li");
    emptyEl.className = "team-list-item";
    emptyEl.textContent = "No teams yet. Create your first team.";
    teamListEl.appendChild(emptyEl);
    return;
  }

  state.teams.forEach((team) => {
    const listItem = teamListTemplate.content.firstElementChild.cloneNode(true);
    const button = listItem.querySelector(".team-select");
    const meta = listItem.querySelector(".team-meta");
    button.textContent = team.name;
    meta.textContent = `${team.member_count} member${team.member_count === 1 ? "" : "s"}`;

    if (team.id === state.selectedTeamId) {
      listItem.classList.add("selected");
    }

    button.addEventListener("click", () => selectTeam(team.id));
    teamListEl.appendChild(listItem);
  });
};

const selectTeam = async (teamId) => {
  state.selectedTeamId = teamId;
  renderTeamList();
  await loadTeamDetails(teamId);
};

const loadTeamDetails = async (teamId) => {
  try {
    const response = await fetch(`/api/teams/${teamId}`);
    const team = await handleResponse(response);

    updateTeamForm.name.value = team.name;
    updateTeamForm.description.value = team.description || "";
    teamDetailsTitle.textContent = team.name;
    memberCountEl.textContent = team.members.length;

    renderMembers(team.members);
    teamDetailsPanel.hidden = false;
    emptyState.hidden = true;
  } catch (error) {
    showToast(error.message, "error");
  }
};

const renderMembers = (members) => {
  memberListEl.innerHTML = "";

  if (!members.length) {
    const empty = document.createElement("li");
    empty.className = "member-item";
    empty.innerHTML = "<p>No members yet. Add someone to this team.</p>";
    memberListEl.appendChild(empty);
    return;
  }

  members
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name))
    .forEach((member) => {
      const item = memberTemplate.content.firstElementChild.cloneNode(true);
      item.dataset.memberId = member.id;
      item.querySelector("h4").textContent = member.name;
      item.querySelector(".member-email").textContent = member.email;
      item.querySelector(".member-role").textContent = member.role ? `Role: ${member.role}` : "";
      item.querySelector(".member-joined").textContent = `Joined ${formatDate(member.joined_at)}`;

      item.querySelector(".member-edit").addEventListener("click", () => onEditMember(member));
      item.querySelector(".member-delete").addEventListener("click", () => onDeleteMember(member));

      memberListEl.appendChild(item);
    });
};

const onEditMember = async (member) => {
  const name = window.prompt("Member name", member.name);
  if (name === null) return;
  const email = window.prompt("Member email", member.email);
  if (email === null) return;
  const role = window.prompt("Member role", member.role || "");
  if (role === null) return;

  try {
    const response = await fetch(`/api/members/${member.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, role }),
    });
    await handleResponse(response);
    showToast("Member updated");
    if (state.selectedTeamId) {
      await selectTeam(state.selectedTeamId);
    }
  } catch (error) {
    showToast(error.message, "error");
  }
};

const onDeleteMember = async (member) => {
  const confirmed = window.confirm(`Remove ${member.name} from the team?`);
  if (!confirmed) return;

  try {
    const response = await fetch(`/api/members/${member.id}`, {
      method: "DELETE",
    });
    await handleResponse(response);
    showToast("Member removed");
    if (state.selectedTeamId) {
      await selectTeam(state.selectedTeamId);
    }
  } catch (error) {
    showToast(error.message, "error");
  }
};

const fetchTeams = async () => {
  try {
    const response = await fetch("/api/teams");
    state.teams = await handleResponse(response);
    renderTeamList();
  } catch (error) {
    showToast(error.message, "error");
  }
};

createTeamForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(createTeamForm);
  const payload = Object.fromEntries(formData.entries());

  try {
    const response = await fetch("/api/teams", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const team = await handleResponse(response);
    showToast("Team created");
    createTeamForm.reset();
    await fetchTeams();
    await selectTeam(team.id);
  } catch (error) {
    showToast(error.message, "error");
  }
});

updateTeamForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedTeamId) return;

  const formData = new FormData(updateTeamForm);
  const payload = Object.fromEntries(formData.entries());

  try {
    const response = await fetch(`/api/teams/${state.selectedTeamId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await handleResponse(response);
    showToast("Team updated");
    await fetchTeams();
    await selectTeam(state.selectedTeamId);
  } catch (error) {
    showToast(error.message, "error");
  }
});

addMemberForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.selectedTeamId) return;

  const formData = new FormData(addMemberForm);
  const payload = Object.fromEntries(formData.entries());

  try {
    const response = await fetch(`/api/teams/${state.selectedTeamId}/members`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await handleResponse(response);
    showToast("Member added");
    addMemberForm.reset();
    await selectTeam(state.selectedTeamId);
  } catch (error) {
    showToast(error.message, "error");
  }
});

deleteTeamButton.addEventListener("click", async () => {
  if (!state.selectedTeamId) return;
  const team = state.teams.find((item) => item.id === state.selectedTeamId);
  const confirmed = window.confirm(`Delete team "${team?.name ?? "this team"}"?`);
  if (!confirmed) return;

  try {
    const response = await fetch(`/api/teams/${state.selectedTeamId}`, {
      method: "DELETE",
    });
    await handleResponse(response);
    showToast("Team deleted");
    state.selectedTeamId = null;
    teamDetailsPanel.hidden = true;
    emptyState.hidden = false;
    await fetchTeams();
  } catch (error) {
    showToast(error.message, "error");
  }
});

refreshTeamsButton.addEventListener("click", () => {
  fetchTeams();
});

window.addEventListener("DOMContentLoaded", async () => {
  await fetchTeams();
  if (state.teams.length) {
    selectTeam(state.teams[0].id);
  }
});
