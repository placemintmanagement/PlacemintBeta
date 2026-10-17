// Header.jsx's sign-out (2026-10, "wire /login to Auth0" pass): the legacy
// logout() alone only clears the app's own session state -- if the visitor
// actually signed in via Auth0, its own hosted session (and SDK cache)
// would still be live, silently signing them back in on the very next page
// load via Auth0TokenSync. doSignOut must also call Auth0's own logout()
// when the visitor is Auth0-authenticated.
import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";

import Header from "./Header";
import { useAuth } from "../auth";

jest.mock("../auth", () => ({ useAuth: jest.fn() }));
jest.mock("@auth0/auth0-react", () => ({ useAuth0: jest.fn() }));

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

const SIGNED_IN_USER = { user_id: "u1", plan: "free", runs_quota: 3, runs_used: 1 };

beforeEach(() => {
  jest.clearAllMocks();
});

async function signOutThroughConfirmDialog(user) {
  await user.click(screen.getByTestId("nav-logout"));
  await user.click(screen.getByTestId("signout-confirm"));
}

test("signed in via Auth0: sign-out calls both the legacy logout() and Auth0's logout(), and does not navigate itself", async () => {
  const logout = jest.fn().mockResolvedValue(undefined);
  const auth0Logout = jest.fn();
  useAuth.mockReturnValue({ user: SIGNED_IN_USER, logout });
  useAuth0.mockReturnValue({ isAuthenticated: true, logout: auth0Logout });

  const user = userEvent.setup();
  render(<MemoryRouter><Header /></MemoryRouter>);
  await signOutThroughConfirmDialog(user);

  expect(logout).toHaveBeenCalledTimes(1);
  expect(auth0Logout).toHaveBeenCalledWith({ logoutParams: { returnTo: window.location.origin } });
  // Auth0's logout() does a full-page redirect -- this component must not
  // also navigate client-side, which would race/interfere with that.
  expect(mockNavigate).not.toHaveBeenCalled();
});

test("not Auth0-authenticated (legacy session only): sign-out only calls the legacy logout() and navigates home", async () => {
  const logout = jest.fn().mockResolvedValue(undefined);
  const auth0Logout = jest.fn();
  useAuth.mockReturnValue({ user: SIGNED_IN_USER, logout });
  useAuth0.mockReturnValue({ isAuthenticated: false, logout: auth0Logout });

  const user = userEvent.setup();
  render(<MemoryRouter><Header /></MemoryRouter>);
  await signOutThroughConfirmDialog(user);

  expect(logout).toHaveBeenCalledTimes(1);
  expect(auth0Logout).not.toHaveBeenCalled();
  expect(mockNavigate).toHaveBeenCalledWith("/");
});
