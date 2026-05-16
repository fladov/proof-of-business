(() => {
  const root = document.documentElement;
  const apiPrefix = document.body?.dataset.apiPrefix || "/api";
  const themeToggleButtons = document.querySelectorAll("[data-theme-toggle]");
  const tabPanels = document.querySelectorAll("[data-tab-panel]");
  const menuButton = document.querySelector("[data-tab-menu]");
  const menuPanel = document.querySelector("[data-tab-menu-panel]");
  const menuOptions = document.querySelectorAll("[data-show-tab]");
  const currentTabLabel = document.querySelector("[data-current-tab-label]");
  const themeIcons = document.querySelectorAll("[data-theme-icon]");
  const paymentForms = document.querySelectorAll("[data-payment-form]");
  const paymentAlert = document.querySelector("[data-payment-alert]");
  const subscoreButtons = document.querySelectorAll("[data-subscore-toggle]");
  const searchInput = document.querySelector("[data-fladov-search-input]");
  const searchResults = document.querySelector("[data-fladov-search-results]");
  const searchStatus = document.querySelector("[data-fladov-search-status]");
  const searchLimit = 10;
  let searchController = null;
  let searchTimer = null;

  const moonIcon = `
    <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M17.293 13.293A8 8 0 0 1 6.707 2.707a.75.75 0 0 0-.982.982A6.5 6.5 0 1 0 16.31 14.275a.75.75 0 0 0 .982-.982Z"></path>
    </svg>
  `;
  const sunIcon = `
    <svg class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 4.25a.75.75 0 0 1 .75.75v1.1a.75.75 0 0 1-1.5 0V5A.75.75 0 0 1 10 4.25Zm0 8.9a.75.75 0 0 1 .75.75V15a.75.75 0 0 1-1.5 0v-1.1a.75.75 0 0 1 .75-.75ZM15 10a.75.75 0 0 1 .75.75.75.75 0 0 1-.75.75h-1.1a.75.75 0 0 1 0-1.5H15ZM6.1 10a.75.75 0 0 1 .75.75.75.75 0 0 1-.75.75H5a.75.75 0 0 1 0-1.5h1.1Zm6.576-3.826a.75.75 0 0 1 1.06 0l.778.778a.75.75 0 1 1-1.06 1.06l-.778-.777a.75.75 0 0 1 0-1.061Zm-7.19 7.19a.75.75 0 0 1 1.06 0l.778.778a.75.75 0 0 1-1.06 1.06l-.778-.777a.75.75 0 0 1 0-1.061Zm7.968 0a.75.75 0 0 1 1.06 0 .75.75 0 0 1 0 1.06l-.778.778a.75.75 0 1 1-1.06-1.06l.778-.778ZM6.546 6.174a.75.75 0 0 1 0 1.06l-.778.778a.75.75 0 0 1-1.06-1.06l.777-.777a.75.75 0 0 1 1.061 0ZM10 7a3 3 0 1 1 0 6 3 3 0 0 1 0-6Z"></path>
    </svg>
  `;

  const setTheme = (theme) => {
    root.dataset.theme = theme;
    root.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem("pob-theme", theme);
    themeIcons.forEach((icon) => {
      icon.innerHTML = theme === "dark" ? sunIcon : moonIcon;
    });
  };

  const savedTheme = window.localStorage.getItem("pob-theme");
  if (savedTheme) {
    setTheme(savedTheme);
  } else {
    setTheme(root.dataset.theme || "light");
  }

  themeToggleButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const next = root.dataset.theme === "dark" ? "light" : "dark";
      setTheme(next);
    });
  });

  const showTab = (tabKey) => {
    tabPanels.forEach((panel) => {
      panel.hidden = panel.dataset.tabPanel !== tabKey;
    });

    if (currentTabLabel) {
      const selected = Array.from(menuOptions).find((button) => button.dataset.showTab === tabKey);
      currentTabLabel.textContent = selected ? selected.dataset.tabTitle || selected.textContent.trim() : tabKey;
    }
  };

  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);

  const renderSearchBusinesses = (items, query) => {
    if (!searchResults) {
      return;
    }

    if (!query) {
      searchResults.innerHTML = "";
      return;
    }

    if (!items.length) {
      searchResults.innerHTML = `
        <div class="rounded-xl border border-dashed border-slate-200 bg-slate-50/70 px-4 py-6 text-sm text-slate-500 dark:border-white/10 dark:bg-white/5 dark:text-slate-400">
          No Fladov businesses match this search.
        </div>
      `;
      return;
    }

    searchResults.innerHTML = items
      .map((item) => {
        const slug = escapeHtml(item.slug);
        const displayName = escapeHtml(item.display_name);
        const avatarUrl = escapeHtml(item.avatar_url);
        const profileUrl = escapeHtml(item.profile_url || `https://fladov.com/biz/${item.slug}`);
        return `
          <article class="rounded-xl border border-slate-200/80 bg-white/90 p-4 transition hover:border-brand-200 dark:border-white/10 dark:bg-white/5">
            <div class="flex items-start gap-3">
              <img src="${avatarUrl}" alt="${displayName} avatar" class="h-12 w-12 rounded-xl border border-slate-200 object-cover dark:border-white/10" loading="lazy" referrerpolicy="no-referrer" data-avatar-fallback="${escapeHtml(item.avatar_placeholder_url || "")}" onerror="this.onerror=null;this.src=this.dataset.avatarFallback;" />
              <div class="min-w-0 flex-1">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <a href="/passport/${slug}" class="block truncate font-display text-lg font-bold tracking-tight text-slate-950 transition hover:text-brand-700 dark:text-white dark:hover:text-brand-300">${displayName}</a>
                    <p class="truncate text-sm text-slate-500 dark:text-slate-400">fladov.com/biz/${slug}</p>
                  </div>
                  <a href="${profileUrl}" class="inline-flex rounded-lg border border-slate-200/80 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:border-brand-200 hover:text-brand-700 dark:border-white/10 dark:text-slate-300 dark:hover:border-brand-400/40 dark:hover:text-brand-200">Profile</a>
                </div>
                <div class="mt-4 flex flex-wrap gap-2">
                  <a href="/passport/${slug}" class="inline-flex items-center rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-700">Open passport</a>
                  <a href="${profileUrl}" class="inline-flex items-center rounded-lg border border-slate-200/80 px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:border-brand-200 hover:text-brand-700 dark:border-white/10 dark:text-slate-300 dark:hover:border-brand-400/40 dark:hover:text-brand-200">View profile</a>
                </div>
              </div>
            </div>
          </article>
        `;
      })
      .join("");
  };

  const loadBusinesses = async (query = "") => {
    if (!searchResults) {
      return;
    }

    if (searchController) {
      searchController.abort();
    }
    searchController = new AbortController();

    if (!query) {
      renderSearchBusinesses([], "");
      if (searchStatus) {
        searchStatus.textContent = "Start typing to search";
      }
      return;
    }

    if (searchStatus) {
      searchStatus.textContent = "Searching...";
    }

    try {
      const response = await fetch(`${apiPrefix}/fladov/businesses?query=${encodeURIComponent(query)}&limit=${searchLimit}`, {
        signal: searchController.signal,
      });
      if (!response.ok) {
        throw new Error("Unable to load Fladov businesses.");
      }
      const data = await response.json();
      const businesses = Array.isArray(data.pob_enabled_businesses) ? data.pob_enabled_businesses : [];
      renderSearchBusinesses(businesses, query);
      if (searchStatus) {
        searchStatus.textContent = businesses.length ? `Showing up to ${searchLimit} results` : "No businesses found.";
      }
    } catch (error) {
      if (error.name === "AbortError") {
        return;
      }
      renderSearchBusinesses([], query);
      if (searchStatus) {
        searchStatus.textContent = error.message || "Unable to load businesses.";
      }
    }
  };

  if (menuButton && menuPanel) {
    menuPanel.classList.add("hidden");

    menuButton.addEventListener("click", () => {
      const isOpen = !menuPanel.classList.contains("hidden");
      menuPanel.classList.toggle("hidden", isOpen);
      menuButton.setAttribute("aria-expanded", String(!isOpen));
    });

    document.addEventListener("click", (event) => {
      if (!menuPanel.contains(event.target) && !menuButton.contains(event.target)) {
        menuPanel.classList.add("hidden");
        menuButton.setAttribute("aria-expanded", "false");
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        menuPanel.classList.add("hidden");
        menuButton.setAttribute("aria-expanded", "false");
      }
    });
  }

  menuOptions.forEach((button) => {
    button.addEventListener("click", () => {
      showTab(button.dataset.showTab);
      if (menuPanel) {
        menuPanel.classList.add("hidden");
      }
      if (menuButton) {
        menuButton.setAttribute("aria-expanded", "false");
      }
    });
  });

  if (tabPanels.length > 0) {
    const defaultPanel = Array.from(tabPanels).find((panel) => !panel.hidden) || tabPanels[0];
    if (defaultPanel) {
      showTab(defaultPanel.dataset.tabPanel);
    }
  }

  if (searchInput && searchResults) {
    renderSearchBusinesses([], "");
    if (searchStatus) {
      searchStatus.textContent = "Start typing to search";
    }
    searchInput.addEventListener("input", () => {
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(() => {
        loadBusinesses(searchInput.value.trim());
      }, 250);
    });
  }

  subscoreButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const panelKey = button.dataset.subscoreToggle;
      const panel = document.querySelector(`[data-subscore-panel="${panelKey}"]`);
      const icon = document.querySelector(`[data-subscore-icon="${panelKey}"]`);

      if (!panel) {
        return;
      }

      const shouldOpen = panel.classList.contains("hidden");
      panel.classList.toggle("hidden", !shouldOpen);
      button.setAttribute("aria-expanded", String(shouldOpen));

      const title = button.querySelector("p");
      if (title) {
        title.textContent = shouldOpen ? "Hide contributing sub scores" : "Show contributing sub scores";
      }

      if (icon) {
        icon.style.transform = shouldOpen ? "rotate(180deg)" : "rotate(0deg)";
      }
    });
  });

  paymentForms.forEach((paymentForm) => {
    const paymentSection = document.querySelector("[data-payment-section]");
    const amountInput = paymentForm.querySelector("input[name='amount']");
    const scrollToPayment = paymentSection?.dataset.scrollIntoView === "true";
    if (scrollToPayment && amountInput) {
      window.requestAnimationFrame(() => {
        paymentSection?.scrollIntoView({ behavior: "smooth", block: "start" });
        amountInput.focus({ preventScroll: true });
        amountInput.select();
      });
    }

    paymentForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submitButton = paymentForm.querySelector("button[type='submit']");
      const noteInput = paymentForm.querySelector("input[name='note']");
      const payload = {
        business_slug: paymentForm.dataset.reportBusinessSlug,
        business_name: paymentForm.dataset.reportBusinessName,
        amount: Number(amountInput.value),
        currency: "NGN",
        theme: paymentForm.dataset.reportTheme || "light",
        note: noteInput.value || null,
        return_url: paymentForm.dataset.paymentReturnUrl,
        invoice_id: paymentForm.dataset.reportInvoiceId || null,
      };

      submitButton.disabled = true;
      submitButton.textContent = "Preparing checkout...";

      try {
        const response = await fetch(`${apiPrefix}/payments/intents`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          throw new Error("Unable to create payment intent.");
        }
        const data = await response.json();
        const checkoutUrl = data.checkout_url || data.payment?.checkout_url;
        if (!checkoutUrl) {
          throw new Error("No checkout URL returned.");
        }
        window.location.href = checkoutUrl;
      } catch (error) {
        submitButton.disabled = false;
        submitButton.textContent = "Make payment";
        window.alert(error.message || "Payment could not be started.");
      }
    });
  });

  if (paymentAlert) {
    const params = new URLSearchParams(window.location.search);
    const result = params.get("payment_result");
    const message = params.get("payment_notice");
    if (result) {
      const normalized = result.toLowerCase();
      const isSuccess = normalized === "succeeded" || normalized === "success";
      const isFailure = ["failed", "cancelled", "canceled", "expired", "error"].includes(normalized);
      const fallbackMessage = isSuccess
        ? "Payment confirmed and recorded."
        : isFailure
          ? "Payment did not complete."
          : "Payment status is being confirmed.";

      paymentAlert.hidden = false;
      paymentAlert.classList.remove("hidden");
      paymentAlert.className = `mb-6 flex items-start gap-4 rounded-xl border px-5 py-4 ${
        isSuccess
          ? "border-emerald-200 bg-emerald-50/90 text-emerald-900 dark:border-emerald-400/20 dark:bg-emerald-500/10 dark:text-emerald-100"
          : isFailure
            ? "border-rose-200 bg-rose-50/90 text-rose-900 dark:border-rose-400/20 dark:bg-rose-500/10 dark:text-rose-100"
            : "border-amber-200 bg-amber-50/90 text-amber-900 dark:border-amber-400/20 dark:bg-amber-500/10 dark:text-amber-100"
      }`;
      paymentAlert.innerHTML = `
        <div class="flex h-11 w-11 flex-none items-center justify-center rounded-lg ${
          isSuccess ? "bg-emerald-600 text-white" : isFailure ? "bg-rose-600 text-white" : "bg-amber-500 text-white"
        }">
          <span class="text-lg font-semibold">${isSuccess ? "OK" : isFailure ? "!" : "..."}</span>
        </div>
        <div class="space-y-1">
          <strong class="block text-sm font-semibold uppercase tracking-[0.2em]">${
            isSuccess ? "Payment successful" : isFailure ? "Payment not completed" : "Payment processing"
          }</strong>
          <p class="text-sm leading-6 opacity-90">${message || fallbackMessage}</p>
        </div>
      `;
      params.delete("payment_result");
      params.delete("payment_notice");
      params.delete("payment_status");
      params.delete("payment_intent");
      const nextUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}${window.location.hash || ""}`;
      window.history.replaceState({}, document.title, nextUrl);
    }
  }
})();
