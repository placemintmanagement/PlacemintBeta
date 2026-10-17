// Auth0TokenSync (2026-10, "wire /login to Auth0" pass): keeps
// auth0TokenBridge's token getter in sync AND re-runs the app's own
// useAuth()'s refresh()/setUser() on every Auth0 auth-state transition --
// this is what makes a real Auth0 sign-in actually populate the app's own
// `user` (college/plan/runs_used/...), and what clears it again on sign-out
// so a stale, now-unauthenticated `user` doesn't linger.
import React from "react";
import { render } from "@testing-library/react";
import { useAuth0 } from "@auth0/auth0-react";

import Auth0TokenSync from "./Auth0TokenSync";
import { setAuth0TokenGetter } from "./auth0TokenBridge";
import { useAuth } from "../auth";

jest.mock("@auth0/auth0-react", () => ({ useAuth0: jest.fn() }));
jest.mock("./auth0TokenBridge", () => ({ setAuth0TokenGetter: jest.fn() }));
jest.mock("../auth", () => ({ useAuth: jest.fn() }));

beforeEach(() => {
  jest.clearAllMocks();
});

test("authenticated: sets the real token getter and refreshes useAuth()'s user", () => {
  const getAccessTokenSilently = jest.fn();
  const refresh = jest.fn();
  const setUser = jest.fn();
  useAuth0.mockReturnValue({ isAuthenticated: true, getAccessTokenSilently });
  useAuth.mockReturnValue({ refresh, setUser });

  render(<Auth0TokenSync />);

  expect(setAuth0TokenGetter).toHaveBeenCalledWith(getAccessTokenSilently);
  expect(refresh).toHaveBeenCalledTimes(1);
  expect(setUser).not.toHaveBeenCalled();
});

test("not authenticated: clears the token getter and the app's own user, does not refresh", () => {
  const getAccessTokenSilently = jest.fn();
  const refresh = jest.fn();
  const setUser = jest.fn();
  useAuth0.mockReturnValue({ isAuthenticated: false, getAccessTokenSilently });
  useAuth.mockReturnValue({ refresh, setUser });

  render(<Auth0TokenSync />);

  expect(setAuth0TokenGetter).toHaveBeenCalledWith(null);
  expect(setUser).toHaveBeenCalledWith(null);
  expect(refresh).not.toHaveBeenCalled();
});

test("sign-out transition (authenticated -> not): re-clears on the next render", () => {
  const refresh = jest.fn();
  const setUser = jest.fn();
  useAuth0.mockReturnValue({ isAuthenticated: true, getAccessTokenSilently: jest.fn() });
  useAuth.mockReturnValue({ refresh, setUser });
  const { rerender } = render(<Auth0TokenSync />);
  expect(refresh).toHaveBeenCalledTimes(1);

  useAuth0.mockReturnValue({ isAuthenticated: false, getAccessTokenSilently: jest.fn() });
  rerender(<Auth0TokenSync />);

  expect(setUser).toHaveBeenCalledWith(null);
  expect(refresh).toHaveBeenCalledTimes(1); // still just the one call from the authenticated render
});
