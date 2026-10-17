// Login.jsx (2026-10, "wire /login to Auth0" pass): Auth0's loginWithRedirect
// is now the primary, default sign-in CTA -- the legacy Google-session/
// email-password UI is still present but collapsed under an "Other sign-in
// options" disclosure (untouched code, just no longer the default path,
// since it issues a session server.py's require_user no longer accepts).
import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";

import Login from "./Login";
import { useAuth } from "../auth";
import { TID } from "../testIds";

jest.mock("../auth", () => ({ useAuth: jest.fn() }));
jest.mock("@auth0/auth0-react", () => ({ useAuth0: jest.fn() }));

beforeEach(() => {
  jest.clearAllMocks();
  useAuth.mockReturnValue({ setUser: jest.fn() });
});

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  );
}

test("the primary CTA calls Auth0's loginWithRedirect, returning to /dashboard", async () => {
  const loginWithRedirect = jest.fn();
  useAuth0.mockReturnValue({ loginWithRedirect });
  const user = userEvent.setup();
  renderLogin();

  await user.click(screen.getByTestId(TID.loginAuth0));

  expect(loginWithRedirect).toHaveBeenCalledWith({ appState: { returnTo: "/dashboard" } });
});

test("the legacy Google/email-password options are still present, just collapsed by default", async () => {
  useAuth0.mockReturnValue({ loginWithRedirect: jest.fn() });
  const user = userEvent.setup();
  renderLogin();

  expect(screen.queryByTestId(TID.loginGoogle)).not.toBeVisible();
  await user.click(screen.getByText(/Other sign-in options/i));
  expect(screen.getByTestId(TID.loginGoogle)).toBeVisible();
  expect(screen.getByTestId(TID.loginEmail)).toBeInTheDocument();
  expect(screen.getByTestId(TID.loginPassword)).toBeInTheDocument();
});
