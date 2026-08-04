"""
A Department (Communications, Finance, Organizing, Legal Affairs, Women's
Affairs, Youth Affairs, Elections, Membership, Research, IT, ...) exists
once as a definition, then runs its own chain of command *parallel to*
the geographic hierarchy: a DepartmentAssignment ties a User to a
Department at a specific OrganizationalUnit (National, a Region, a
Constituency, a Branch, ...) with a position.

Authority rule (see apps.departments.permissions.has_department_authority):
a HEAD or DEPUTY_HEAD of a department at unit U may manage (add/remove)
department assignments and assign tasks for that department at U *and any
descendant of U*. This gives exactly the behaviour requested:

- The National Communications Director (HEAD, Communications, @ NATIONAL)
  can add National Communications team MEMBERs, appoint/remove Regional
  Communications Directors, and reach all the way down to Branch level.
- A Regional Communications Director (HEAD, Communications, @ a REGIONAL
  unit) can add Regional team members and reach down into that region's
  constituencies/branches, but cannot touch another region or appoint
  anyone at NATIONAL level.
- A Constituency/District departmental officer (HEAD, @ a CONSTITUENCY
  unit) can add/remove that department's Branch-level members within
  their own constituency, per the same rule.
"""

POSITION_CHOICES = [
    ("HEAD", "Head / Director"),
    ("DEPUTY_HEAD", "Deputy Head / Deputy Director"),
    ("OFFICER", "Officer"),
    ("MEMBER", "Team Member"),
]

# Positions that carry management authority over their unit's subtree.
AUTHORITY_POSITIONS = ["HEAD", "DEPUTY_HEAD"]

ENGAGEMENT_TYPE_CHOICES = [
    ("TV", "Television"),
    ("RADIO", "Radio / FM"),
    ("PRINT", "Print Media"),
    ("ONLINE", "Online / Social Media"),
    ("EVENT", "Event / Public Engagement"),
    ("OTHER", "Other"),
]

TASK_STATUS_CHOICES = [
    ("PENDING", "Pending"),
    ("ACKNOWLEDGED", "Acknowledged"),
    ("COMPLETED", "Completed"),
    ("CANCELLED", "Cancelled"),
]
