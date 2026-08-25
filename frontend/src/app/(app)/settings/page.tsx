"use client";

import Link from "next/link";
import { Shield } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProfileForm } from "@/components/settings/profile-form";
import { ChangePasswordForm } from "@/components/settings/change-password-form";
import { SetKioskPinForm } from "@/components/settings/set-kiosk-pin-form";
import { NotificationPreferencesForm } from "@/components/settings/notification-preferences-form";
import { AuditLogTab } from "@/components/settings/audit-log-tab";
import { ThemeSwitcher } from "@/components/layout/theme-switcher";
import { useAuthStore } from "@/stores/auth-store";

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const isNationalOfficer = user?.is_superadmin || user?.role?.scope === "NATIONAL";
  const canManagePositions =
    user?.is_superadmin || (user?.role?.permissions.includes("hierarchy.manage_roles") ?? false);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-display font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground">Your account, notifications, and preferences</p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="security">Security</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="appearance">Appearance</TabsTrigger>
          {isNationalOfficer && <TabsTrigger value="audit">Audit Log</TabsTrigger>}
        </TabsList>

        <TabsContent value="profile">
          {!user ? (
            <Skeleton className="h-64" />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Profile</CardTitle>
                <CardDescription>
                  {user.membership_id} · {user.role?.name ?? "Ordinary Member"}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ProfileForm user={user} />
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="security" className="flex flex-col gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Change Password</CardTitle>
            </CardHeader>
            <CardContent>
              <ChangePasswordForm />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Kiosk Voting PIN</CardTitle>
            </CardHeader>
            <CardContent>
              <SetKioskPinForm />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notifications">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Delivery Channels</CardTitle>
              <CardDescription>
                Choose how you want to be notified. In-app notifications are always on.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <NotificationPreferencesForm />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="appearance">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Appearance & Language</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              <div className="flex items-center justify-between rounded-lg border border-border p-3">
                <span className="text-sm font-medium">Theme</span>
                <ThemeSwitcher />
              </div>
              {canManagePositions && (
                <div className="flex items-center justify-between rounded-lg border border-border p-3">
                  <div className="flex items-center gap-2">
                    <Shield className="size-4 text-primary" />
                    <span className="text-sm font-medium">Position Management</span>
                  </div>
                  <Button asChild variant="outline" size="sm">
                    <Link href="/settings/positions">Manage Positions</Link>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {isNationalOfficer && (
          <TabsContent value="audit">
            <AuditLogTab />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
