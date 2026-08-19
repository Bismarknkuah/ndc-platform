import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import 'groups_provider.dart';

class GroupMessagesScreen extends StatelessWidget {
  const GroupMessagesScreen({super.key, required this.groupId, required this.groupName});

  final String groupId;
  final String groupName;

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => GroupMessagesProvider()..load(groupId),
      child: _GroupMessagesView(groupId: groupId, groupName: groupName),
    );
  }
}

class _GroupMessagesView extends StatefulWidget {
  const _GroupMessagesView({required this.groupId, required this.groupName});

  final String groupId;
  final String groupName;

  @override
  State<_GroupMessagesView> createState() => _GroupMessagesViewState();
}

class _GroupMessagesViewState extends State<_GroupMessagesView> {
  final _messageController = TextEditingController();

  @override
  void dispose() {
    _messageController.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _messageController.text.trim();
    if (text.isEmpty) return;
    _messageController.clear();
    await context.read<GroupMessagesProvider>().send(widget.groupId, text);
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<GroupMessagesProvider>();
    final timeFormat = DateFormat('h:mm a');

    return Scaffold(
      appBar: AppBar(title: Text(widget.groupName)),
      body: Column(
        children: [
          Expanded(
            child: Builder(
              builder: (context) {
                if (provider.isLoading && provider.messages.isEmpty) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (provider.messages.isEmpty) {
                  return const Center(child: Text('No messages yet. Say hello!'));
                }
                // Newest-first from the API; reverse for a natural chat feed.
                final ordered = provider.messages.reversed.toList();
                return ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: ordered.length,
                  itemBuilder: (context, index) {
                    final message = ordered[index];
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            message.senderName,
                            style: Theme.of(context).textTheme.labelMedium,
                          ),
                          Text(message.body),
                          Text(
                            timeFormat.format(message.createdAt),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    );
                  },
                );
              },
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _messageController,
                      decoration: const InputDecoration(
                        hintText: 'Type a message...',
                        border: OutlineInputBorder(),
                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      ),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    onPressed: provider.isSending ? null : _send,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
