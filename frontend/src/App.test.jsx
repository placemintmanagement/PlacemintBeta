// Unit tests for App.js's `Protected` route guard (2026-10, "wire /login to
// Auth0" pass): it now gates on BOTH the app's own useAuth() context AND
// Auth0's isAuthenticated/isLoading, specifically to avoid bouncing a
// genuinely authenticated visitor to /login during the brief window after
// Auth0 resolves a real session but BEFORE Auth0TokenSync's re-run of
// useAuth()'s refresh() (GET /auth/me) completes. Exercised directly
// against the exported `Protected` component (not the full route tree) so
// this doesn't need to mock every page App.js imports.
import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";

import { Protected } from "./App";
import { useAuth } from "./auth";
import { useAuth0 } from "@auth0/auth0-react";

jest.mock("./auth", () => ({ useAuth: jest.fn() }));
jest.mock("@auth0/auth0-react", () => ({ useAuth0: jest.fn() }));

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={["/secret"]}>
      <Routes>
        <Route path="/secret" element={<Protected><div>secret content</div></Protected>} />
        <Route path="/login" element={<div>login page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
});

test("shows Loading while the legacy auth context is still resolving", () => {
  useAuth.mockReturnValue({ user: null, loading: true });
  useAuth0.mockReturnValue({ isLoading: false, isAuthenticated: false });
  renderProtected();
  expect(screen.getByText(/Loading/i)).toBeInTheDocument();
});

test("shows Loading while Auth0 is still resolving, even if the legacy context already settled", () => {
  useAuth.mockReturnValue({ user: null, loading: false });
  useAuth0.mockReturnValue({ isLoading: true, isAuthenticated: false });
  renderProtected();
  expect(screen.getByText(/Loading/i)).toBeInTheDocument();
});

test("Auth0 says authenticated but useAuth()'s user hasn't caught up yet: shows Loading, does NOT redirect", () => {
  // The exact race this change fixes -- Auth0TokenSync's refresh() hasn't
  // resolved yet. Must not bounce to /login.
  useAuth.mockReturnValue({ user: null, loading: false });
  useAuth0.mockReturnValue({ isLoading: false, isAuthenticated: true });
  renderProtected();
  expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  expect(screen.queryByText("login page")).not.toBeInTheDocument();
});

test("neither signal is authenticated: redirects to /login", () => {
  useAuth.mockReturnValue({ user: null, loading: false });
  useAuth0.mockReturnValue({ isLoading: false, isAuthenticated: false });
  renderProtected();
  expect(screen.getByText("login page")).toBeInTheDocument();
});

test("both resolved and the user is present: renders children", () => {
  useAuth.mockReturnValue({ user: { user_id: "u1", college: "IIT" }, loading: false });
  useAuth0.mockReturnValue({ isLoading: false, isAuthenticated: true });
  renderProtected();
  expect(screen.getByText("secret content")).toBeInTheDocument();
});
