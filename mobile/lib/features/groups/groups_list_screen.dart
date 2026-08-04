import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'group_messages_screen.dart';
import 'groups_provider.dart';

class GroupsListScreen extends StatefulWidget {
  const GroupsListScreen({super.key});

  @override
  State<GroupsListScreen> createState() => _GroupsListScreenState();
}

class _GroupsListScreenState extends State<GroupsListScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<GroupsProvider>().load();
    });
  }

  Future<void> _createGroup() async {
    final nameController = TextEditingController();
    final descriptionController = TextEditingController();

    final shouldCreate = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('New Discussion Group'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              decoration: const InputDecoration(labelText: 'Group name'),
              autofocus: true,
            ),
            TextField(
              controller: descriptionController,
              decoration: const InputDecoration(labelText: 'Description (optional)'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Create'),
          ),
        ],
      ),
    );

    if (shouldCreate == true && nameController.text.trim().isNotEmpty && mounted) {
      await context.read<GroupsProvider>().createGroup(
            nameController.text.trim(),
            descriptionController.text.trim(),
          );
    }
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<GroupsProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('Discussion Groups')),
      floatingActionButton: FloatingActionButton(
        onPressed: _createGroup,
        child: const Icon(Icons.add),
      ),
      body: Builder(
        builder: (context) {
          if (provider.isLoading && provider.groups.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }
          if (provider.error != null && provider.groups.isEmpty) {
            return Center(child: Text(provider.error!));
          }
          if (provider.groups.isEmpty) {
            return const Center(child: Text('No groups yet. Tap + to start one.'));
          }
          return RefreshIndicator(
            onRefresh: () => context.read<GroupsProvider>().load(),
            child: ListView.separated(
              itemCount: provider.groups.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) {
                final group = provider.groups[index];
                return ListTile(
                  leading: const CircleAvatar(child: Icon(Icons.forum)),
                  title: Text(group.name),
                  subtitle: Text(
                    group.description.isNotEmpty
                        ? group.description
                        : '${group.members.length} members',
                  ),
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) =>
                          GroupMessagesScreen(groupId: group.id, groupName: group.name),
                    ),
                  ),
                );
              },
            ),
          );
        },
      ),
    );
  }
}
