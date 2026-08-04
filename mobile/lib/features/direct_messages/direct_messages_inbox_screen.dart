import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../auth/auth_provider.dart';
import 'conversation_screen.dart';
import 'direct_messages_provider.dart';

class DirectMessagesInboxScreen extends StatefulWidget {
  const DirectMessagesInboxScreen({super.key});

  @override
  State<DirectMessagesInboxScreen> createState() => _DirectMessagesInboxScreenState();
}

class _DirectMessagesInboxScreenState extends State<DirectMessagesInboxScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final currentUserId = context.read<AuthProvider>().currentUser?.id;
      if (currentUserId != null) {
        context.read<DirectMessagesInboxProvider>().load(currentUserId);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<DirectMessagesInboxProvider>();
    final dateFormat = DateFormat('MMM d, h:mm a');

    return Scaffold(
      appBar: AppBar(title: const Text('Messages')),
      body: Builder(
        builder: (context) {
          if (provider.isLoading && provider.conversations.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }
          if (provider.error != null && provider.conversations.isEmpty) {
            return Center(child: Text(provider.error!));
          }
          if (provider.conversations.isEmpty) {
            return const Center(child: Text('No conversations yet.'));
          }
          return ListView.separated(
            itemCount: provider.conversations.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final conversation = provider.conversations[index];
              return ListTile(
                leading: const CircleAvatar(child: Icon(Icons.person)),
                title: Text(conversation.otherPartyName),
                subtitle: Text(
                  conversation.lastMessage.body,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: Text(
                  dateFormat.format(conversation.lastMessage.createdAt),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ConversationScreen(
                      otherUserId: conversation.otherPartyId,
                      otherUserName: conversation.otherPartyName,
                    ),
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}
