"use client"

import React from 'react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
  AlertDialogFooter,
  AlertDialogCancel
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SubmitButton } from "@/components/ui/submit-button";
import { handleSignUp } from './actions';

const SignupPopup = () => {
  const [open, setOpen] = React.useState(false);
  const [message, setMessage] = React.useState<string>("");
  const [isSuccess, setIsSuccess] = React.useState(false);

  const onSubmit = async (formData: FormData) => {
    setMessage(""); 
    setIsSuccess(false);
    try {
      const result = await handleSignUp(formData);
      setMessage(result.message);
      setIsSuccess(result.success);
    } catch (error: any) {
      setMessage(error.message || "An error occurred during signup");
      setIsSuccess(false);
    }
  };

  return (
    <>
      <div className="text-muted-foreground mt-4 flex justify-center text-sm">
        <span className="mr-1">Don't have an account?</span>
        <AlertDialog open={open} onOpenChange={setOpen}>
          <AlertDialogTrigger asChild>
            <button className="text-primary underline hover:opacity-80 p-0 border-none bg-transparent cursor-pointer">
              Sign Up
            </button>
          </AlertDialogTrigger>
          <AlertDialogContent className="sm:max-w-md">
            <AlertDialogHeader>
              <AlertDialogTitle>Create Account</AlertDialogTitle>
              <AlertDialogDescription>
                Fill in your details to create a new account
              </AlertDialogDescription>
            </AlertDialogHeader>
            
            <form action={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="signup-email">Email</Label>
                <Input
                  id="signup-email"
                  name="email"
                  type="email"
                  placeholder="you@example.com"
                  required
                  className="w-full"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="signup-password">Password</Label>
                <Input
                  id="signup-password"
                  name="password"
                  type="password"
                  placeholder="••••••••"
                  required
                  className="w-full"
                />
              </div>
              
              {message && (
                <div className={`p-4 text-center rounded-md ${
                  isSuccess 
                    ? "bg-green-50 text-green-800" 
                    : "bg-foreground/10 text-foreground"
                }`}>
                  {message}
                </div>
              )}
              
              <AlertDialogFooter className="gap-2 sm:gap-0">
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <SubmitButton 
                  className="bg-blue-700 text-white"
                >
                  Create Account
                </SubmitButton>
              </AlertDialogFooter>
            </form>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </>
  );
};

export default SignupPopup;