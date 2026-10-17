// Signup.jsx -- same pass as Login.test.jsx's own comment explains.
import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";

import Signup from "./Signup";
import { useAuth } from "../auth";
import { TID } from "../testIds";

jest.mock("../auth", () => ({ useAuth: jest.fn() }));
jest.mock("@auth0/auth0-react", () => ({ useAuth0: jest.fn() }));

beforeEach(() => {
  jest.clearAllMocks();
  useAuth.mockReturnValue({ setUser: jest.fn() });
});

function renderSignup() {
  return render(
    <MemoryRouter>
      <Signup />
    </MemoryRouter>
  );
}

test("the primary CTA calls Auth0's loginWithRedirect with a signup screen hint", async () => {
  const loginWithRedirect = jest.fn();
  useAuth0.mockReturnValue({ loginWithRedirect });
  const user = userEvent.setup();
  renderSignup();

  await user.click(screen.getByTestId(TID.signupAuth0));

  expect(loginWithRedirect).toHaveBeenCalledWith({
    appState: { returnTo: "/dashboard" },
    authorizationParams: { screen_hint: "signup" },
  });
});

test("the legacy Google/email-password options are still present, just collapsed by default", async () => {
  useAuth0.mockReturnValue({ loginWithRedirect: jest.fn() });
  const user = userEvent.setup();
  renderSignup();

  expect(screen.queryByTestId(TID.signupGoogle)).not.toBeVisible();
  await user.click(screen.getByText(/Other sign-up options/i));
  expect(screen.getByTestId(TID.signupGoogle)).toBeVisible();
  expect(screen.getByTestId(TID.signupName)).toBeInTheDocument();
});
