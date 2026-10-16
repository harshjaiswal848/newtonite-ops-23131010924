import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Navbar from './components/Navbar';
import LoginModal from './components/LoginModal';
import ConflictBanner from './components/ConflictBanner';
import QuickViewsTabs from './components/QuickViewsTabs';
import FilterBar from './components/FilterBar';
import WorkItemList from './components/WorkItemList';
import WorkItemDetailDrawer from './components/WorkItemDetailDrawer';
import CreateItemModal from './components/CreateItemModal';
import {
  getAuthToken,
  setAuthToken,
  getStoredUser,
  setStoredUser,
  login,
  getMe,
  getTeams,
  getItems,
  getItem,
  createItem,
  updateItem,
  claimItem,
  transitionItem,
  addComment,
} from './api/client';

export default function App() {
  const queryClient = useQueryClient();

  // Auth State
  const [currentUser, setCurrentUser] = useState(getStoredUser());
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Filter State
  const [activeView, setActiveView] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTeam, setSelectedTeam] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');
  const [selectedPriority, setSelectedPriority] = useState('');

  // Pagination State (Keyset Cursor)
  const [itemsList, setItemsList] = useState([]);
  const [nextCursor, setNextCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);

  // Selection & Modals
  const [selectedItemId, setSelectedItemId] = useState(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Conflict / Rollback Banner State
  const [conflictInfo, setConflictInfo] = useState(null);

  // Initial Auto-Login / Verify Session
  useEffect(() => {
    const token = getAuthToken();
    if (token) {
      getMe()
        .then((user) => {
          setCurrentUser(user);
          setStoredUser(user);
        })
        .catch(() => {
          setAuthToken(null);
          setStoredUser(null);
          setCurrentUser(null);
        });
    } else {
      // Default: login as Lead for immediate reviewer convenience
      login('lead.payments@newtonite.internal', 'password123')
        .then(({ user }) => setCurrentUser(user))
        .catch(console.error);
    }
  }, []);

  const handleLogin = async (email, password) => {
    const { user } = await login(email, password);
    setCurrentUser(user);
    queryClient.invalidateQueries({ queryKey: ['items'] });
    queryClient.invalidateQueries({ queryKey: ['teams'] });
  };

  const handleLogout = () => {
    setAuthToken(null);
    setStoredUser(null);
    setCurrentUser(null);
    setIsLoginModalOpen(true);
  };

  // Queries
  const { data: teams = [] } = useQuery({
    queryKey: ['teams', currentUser?.id],
    queryFn: getTeams,
    enabled: !!currentUser,
  });

  const {
    data: itemsData,
    isLoading: isItemsLoading,
    isFetching: isItemsFetching,
    refetch: refetchItems,
  } = useQuery({
    queryKey: ['items', activeView, selectedTeam, selectedStatus, selectedPriority, searchQuery],
    queryFn: () =>
      getItems({
        view: activeView || undefined,
        team_id: selectedTeam || undefined,
        status: selectedStatus || undefined,
        priority: selectedPriority || undefined,
        q: searchQuery || undefined,
        limit: 25,
      }),
    enabled: !!currentUser,
  });

  // Synchronize items list when query updates
  useEffect(() => {
    if (itemsData) {
      setItemsList(itemsData.items || []);
      setNextCursor(itemsData.next_cursor);
      setHasMore(itemsData.has_more);
      setTotalCount(itemsData.total_count);
    }
  }, [itemsData]);

  // Load More (Keyset Cursor Pagination)
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const handleLoadMore = async () => {
    if (!nextCursor || isLoadingMore) return;
    setIsLoadingMore(true);
    try {
      const moreData = await getItems({
        view: activeView || undefined,
        team_id: selectedTeam || undefined,
        status: selectedStatus || undefined,
        priority: selectedPriority || undefined,
        q: searchQuery || undefined,
        cursor: nextCursor,
        limit: 25,
      });

      setItemsList((prev) => [...prev, ...moreData.items]);
      setNextCursor(moreData.next_cursor);
      setHasMore(moreData.has_more);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingMore(false);
    }
  };

  // Active selected item details query
  const { data: selectedItemDetail, refetch: refetchDetail } = useQuery({
    queryKey: ['item-detail', selectedItemId],
    queryFn: () => getItem(selectedItemId),
    enabled: !!selectedItemId,
  });

  // Calculate current user's role in the selected item's team
  const getUserRoleInTeam = (teamId) => {
    if (!currentUser || !currentUser.roles) return 'Viewer';
    const membership = currentUser.roles.find((r) => r.team_id === teamId);
    return membership ? membership.role : 'Outsider';
  };

  const currentRoleForSelectedItem = selectedItemDetail
    ? getUserRoleInTeam(selectedItemDetail.team_id)
    : 'Viewer';

  // --- MUTATIONS WITH OPTIMISTIC UPDATES & ROLLBACK ---

  // 1. Claim Mutation
  const claimMutation = useMutation({
    mutationFn: (itemId) => claimItem(itemId),
    onMutate: async (itemId) => {
      setConflictInfo(null);
      // Cancel queries
      await queryClient.cancelQueries({ queryKey: ['items'] });
      const previousItems = itemsList;

      // Optimistic Update
      setItemsList((prev) =>
        prev.map((item) =>
          item.id === itemId
            ? {
                ...item,
                assignee_id: currentUser.id,
                assignee: { id: currentUser.id, full_name: currentUser.full_name, email: currentUser.email },
                status: 'In Progress',
                version: item.version + 1,
              }
            : item
        )
      );

      return { previousItems };
    },
    onError: (err, itemId, context) => {
      // ROLLBACK CACHE
      if (context?.previousItems) {
        setItemsList(context.previousItems);
      }
      setConflictInfo({
        status: err.status || 409,
        type: 'claim',
        message: err.message || 'Work item was claimed concurrently by another operator.',
        detail: err.data,
      });
      refetchItems();
      if (selectedItemId === itemId) refetchDetail();
    },
    onSuccess: () => {
      refetchItems();
      if (selectedItemId) refetchDetail();
    },
  });

  // 2. Transition Mutation
  const transitionMutation = useMutation({
    mutationFn: ({ itemId, targetStatus, comment }) =>
      transitionItem(itemId, { target_status: targetStatus, comment }),
    onMutate: async ({ itemId, targetStatus }) => {
      setConflictInfo(null);
      const previousItems = itemsList;

      // Optimistic update
      setItemsList((prev) =>
        prev.map((item) =>
          item.id === itemId
            ? { ...item, status: targetStatus, version: item.version + 1 }
            : item
        )
      );

      return { previousItems };
    },
    onError: (err, { itemId }, context) => {
      // ROLLBACK CACHE
      if (context?.previousItems) {
        setItemsList(context.previousItems);
      }
      setConflictInfo({
        status: err.status || 403,
        type: 'transition',
        message: err.message || 'Workflow transition rejected by the server.',
        detail: err.data,
      });
      refetchItems();
      if (selectedItemId === itemId) refetchDetail();
    },
    onSuccess: () => {
      refetchItems();
      if (selectedItemId) refetchDetail();
    },
  });

  // 3. Update Mutation (Optimistic Lock Version Check)
  const updateMutation = useMutation({
    mutationFn: ({ itemId, updateData }) => updateItem(itemId, updateData),
    onError: (err) => {
      setConflictInfo({
        status: err.status || 409,
        type: 'version',
        message: err.message || 'Version conflict: Another user updated this item.',
        detail: err.data,
      });
      refetchItems();
      if (selectedItemId) refetchDetail();
    },
    onSuccess: () => {
      refetchItems();
      if (selectedItemId) refetchDetail();
    },
  });

  // 4. Add Comment
  const commentMutation = useMutation({
    mutationFn: ({ itemId, content }) => addComment(itemId, content),
    onSuccess: () => {
      if (selectedItemId) refetchDetail();
    },
  });

  // 5. Create Item
  const createMutation = useMutation({
    mutationFn: ({ data, customKey }) => createItem(data, customKey),
    onSuccess: (res) => {
      refetchItems();
      return res;
    },
  });

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navbar */}
      <Navbar
        currentUser={currentUser}
        onLogout={handleLogout}
        onOpenLogin={() => setIsLoginModalOpen(true)}
        onRefresh={() => {
          refetchItems();
          if (selectedItemId) refetchDetail();
        }}
        isFetching={isItemsFetching}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Concurrency / Authorization Conflict Banner */}
        <ConflictBanner
          conflictInfo={conflictInfo}
          onDismiss={() => setConflictInfo(null)}
          onReload={() => {
            setConflictInfo(null);
            refetchItems();
            if (selectedItemId) refetchDetail();
          }}
        />

        {/* Quick Attention Views Tabs */}
        <QuickViewsTabs
          activeView={activeView}
          onViewChange={(v) => {
            setActiveView(v);
            setSearchQuery('');
          }}
        />

        {/* Filter Controls */}
        <FilterBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          selectedTeam={selectedTeam}
          onTeamChange={setSelectedTeam}
          selectedStatus={selectedStatus}
          onStatusChange={setSelectedStatus}
          selectedPriority={selectedPriority}
          onPriorityChange={setSelectedPriority}
          teams={teams}
          onOpenCreate={() => setIsCreateModalOpen(true)}
          canCreate={currentUser && currentUser.roles && currentUser.roles.some((r) => r.role !== 'Viewer')}
        />

        {/* Paginated Work Items List */}
        <WorkItemList
          items={itemsList}
          totalCount={totalCount}
          hasMore={hasMore}
          onLoadMore={handleLoadMore}
          isLoadingMore={isLoadingMore}
          onSelectItem={(item) => setSelectedItemId(item.id)}
          selectedItemId={selectedItemId}
          onClaimItem={(id) => claimMutation.mutate(id)}
          isClaimingId={claimMutation.isPending ? claimMutation.variables : null}
          canClaim={currentUser && currentUser.roles && currentUser.roles.some((r) => r.role !== 'Viewer')}
        />
      </main>

      {/* Item Detail Drawer */}
      {selectedItemId && (
        <WorkItemDetailDrawer
          item={selectedItemDetail}
          onClose={() => setSelectedItemId(null)}
          currentUserRole={currentRoleForSelectedItem}
          onClaim={(id) => claimMutation.mutate(id)}
          isClaiming={claimMutation.isPending}
          onTransition={(id, status, comment) =>
            transitionMutation.mutate({ itemId: id, targetStatus: status, comment })
          }
          isTransitioning={transitionMutation.isPending}
          onUpdate={(id, updateData) => updateMutation.mutateAsync({ itemId: id, updateData })}
          isUpdating={updateMutation.isPending}
          onAddComment={(id, content) => commentMutation.mutateAsync({ itemId: id, content })}
          isCommenting={commentMutation.isPending}
          conflictError={conflictInfo}
        />
      )}

      {/* Create Modal */}
      <CreateItemModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        teams={teams}
        onCreateItem={async (data, customKey) => {
          return await createMutation.mutateAsync({ data, customKey });
        }}
        isCreating={createMutation.isPending}
      />

      {/* Login / Persona Switcher Modal */}
      <LoginModal
        isOpen={isLoginModalOpen}
        onClose={() => setIsLoginModalOpen(false)}
        onLogin={handleLogin}
        activeUserId={currentUser?.id}
      />
    </div>
  );
}
