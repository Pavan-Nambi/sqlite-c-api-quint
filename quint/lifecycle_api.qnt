module SqliteLifecycleApi {
  type Scenario = str

  val FinalizeNull: Scenario = "finalize_null"
  val CloseNull: Scenario = "close_null"
  val CloseLiveStmt: Scenario = "close_live_stmt"
  val CloseV2LiveStmt: Scenario = "close_v2_live_stmt"
  val PrepareV2V3ZeroFlags: Scenario = "prepare_v2_v3_zero_flags"
  val CloseLiveBackup: Scenario = "close_live_backup"
  val CloseV2LiveBackup: Scenario = "close_v2_live_backup"
  val BackupStepDoneFinish: Scenario = "backup_step_done_finish"
  val BackupFinishIncomplete: Scenario = "backup_finish_incomplete"
  val BackupInitSameConnectionError: Scenario = "backup_init_same_connection_error"
  val BackupInitDestReadTxnError: Scenario = "backup_init_dest_read_txn_error"
  val BackupStepZeroNoProgress: Scenario = "backup_step_zero_no_progress"
  val BackupStepNegativeAllRemainingDone: Scenario = "backup_step_negative_all_remaining_done"
  val BackupStepTransientConflictRetry: Scenario = "backup_step_transient_conflict_retry"

  type ModelState = {
    scenario: Scenario,
    stage: int,
    connOpen: bool,
    connZombie: bool,
    closeNullCalled: bool,
    closeV2NullCalled: bool,
    prepareCaseSelected: bool,
    prepareComparedEqual: bool,
    stmtHandleLive: bool,
    backupHandleLive: bool,
    backupQueryMatched: bool,
    destReadTxnStarted: bool,
  }

  var state: ModelState

  val Scenarios: Set[Scenario] = Set(
    FinalizeNull,
    CloseNull,
    CloseLiveStmt,
    CloseV2LiveStmt,
    PrepareV2V3ZeroFlags,
    CloseLiveBackup,
    CloseV2LiveBackup,
    BackupStepDoneFinish,
    BackupFinishIncomplete,
    BackupInitSameConnectionError,
    BackupInitDestReadTxnError,
    BackupStepZeroNoProgress,
    BackupStepNegativeAllRemainingDone,
    BackupStepTransientConflictRetry
  )

  def startsOpen(scenario: Scenario): bool =
    scenario == CloseLiveStmt
    or scenario == CloseV2LiveStmt
    or scenario == PrepareV2V3ZeroFlags
    or scenario == CloseLiveBackup
    or scenario == CloseV2LiveBackup
    or scenario == BackupStepDoneFinish
    or scenario == BackupFinishIncomplete
    or scenario == BackupInitSameConnectionError
    or scenario == BackupInitDestReadTxnError
    or scenario == BackupStepZeroNoProgress
    or scenario == BackupStepNegativeAllRemainingDone
    or scenario == BackupStepTransientConflictRetry

  def fresh(scenario: Scenario): ModelState = {
    scenario: scenario,
    stage: 0,
    connOpen: startsOpen(scenario),
    connZombie: false,
    closeNullCalled: false,
    closeV2NullCalled: false,
    prepareCaseSelected: false,
    prepareComparedEqual: false,
    stmtHandleLive: false,
    backupHandleLive: false,
    backupQueryMatched: false,
    destReadTxnStarted: false,
  }

  def nextState(
    current: ModelState,
    stage: int,
    connOpen: bool,
    connZombie: bool,
    closeNullCalled: bool,
    closeV2NullCalled: bool,
    prepareCaseSelected: bool,
    prepareComparedEqual: bool,
    stmtHandleLive: bool,
    backupHandleLive: bool,
    backupQueryMatched: bool,
    destReadTxnStarted: bool,
  ): ModelState = {
    scenario: current.scenario,
    stage: stage,
    connOpen: connOpen,
    connZombie: connZombie,
    closeNullCalled: closeNullCalled,
    closeV2NullCalled: closeV2NullCalled,
    prepareCaseSelected: prepareCaseSelected,
    prepareComparedEqual: prepareComparedEqual,
    stmtHandleLive: stmtHandleLive,
    backupHandleLive: backupHandleLive,
    backupQueryMatched: backupQueryMatched,
    destReadTxnStarted: destReadTxnStarted,
  }

  action initDoc = {
    nondet scenario = Scenarios.oneOf()
    state' = fresh(scenario)
  }

  action init = initDoc

  action finalizeNullNoOp = all {
    state.scenario == FinalizeNull,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action closeNullNoOp = all {
    state.scenario == CloseNull,
    not(state.closeNullCalled),
    state' = nextState(
      state,
      state.stage,
      state.connOpen,
      state.connZombie,
      true,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action closeV2NullNoOp = all {
    state.scenario == CloseNull,
    not(state.closeV2NullCalled),
    state' = nextState(
      state,
      state.stage,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      true,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action prepareStmtForClose = all {
    state.scenario == CloseLiveStmt,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      true,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action closeBusyWithLiveStmt = all {
    state.scenario == CloseLiveStmt,
    state.stage == 1,
    state.stmtHandleLive,
    state' = nextState(
      state,
      2,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action stepStmtAfterCloseBusy = all {
    state.scenario == CloseLiveStmt,
    state.stage == 2,
    state.stmtHandleLive,
    state' = nextState(
      state,
      3,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action finalizeStmtAfterCloseBusy = all {
    state.scenario == CloseLiveStmt,
    state.stage == 3,
    state.stmtHandleLive,
    state' = nextState(
      state,
      4,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      false,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action closeAfterFinalize = all {
    state.scenario == CloseLiveStmt,
    state.stage == 4,
    not(state.stmtHandleLive),
    state' = nextState(
      state,
      5,
      false,
      false,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action prepareStmtForCloseV2 = all {
    state.scenario == CloseV2LiveStmt,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      true,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action closeV2MarksZombieWithLiveStmt = all {
    state.scenario == CloseV2LiveStmt,
    state.stage == 1,
    state.stmtHandleLive,
    state' = nextState(
      state,
      2,
      true,
      true,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action stepStmtAfterCloseV2 = all {
    state.scenario == CloseV2LiveStmt,
    state.stage == 2,
    state.stmtHandleLive,
    state.connZombie,
    state' = nextState(
      state,
      3,
      true,
      true,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action finalizeStmtAfterCloseV2 = all {
    state.scenario == CloseV2LiveStmt,
    state.stage == 3,
    state.stmtHandleLive,
    state.connZombie,
    state' = nextState(
      state,
      4,
      false,
      false,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      false,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action selectPrepareCase = all {
    state.scenario == PrepareV2V3ZeroFlags,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      true,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action comparePrepareZeroFlags = all {
    state.scenario == PrepareV2V3ZeroFlags,
    state.stage == 1,
    state.prepareCaseSelected,
    state' = nextState(
      state,
      2,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      true,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action closeAfterPrepareComparison = all {
    state.scenario == PrepareV2V3ZeroFlags,
    state.stage == 2,
    state.prepareComparedEqual,
    state' = nextState(
      state,
      3,
      false,
      false,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupInitForClose = all {
    state.scenario == CloseLiveBackup,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      true,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action closeBusyWithLiveBackup = all {
    state.scenario == CloseLiveBackup,
    state.stage == 1,
    state.backupHandleLive,
    state' = nextState(
      state,
      2,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupStepDoneAfterCloseBusy = all {
    state.scenario == CloseLiveBackup,
    state.stage == 2,
    state.backupHandleLive,
    state' = nextState(
      state,
      3,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupFinishAfterCloseBusy = all {
    state.scenario == CloseLiveBackup,
    state.stage == 3,
    state.backupHandleLive,
    state' = nextState(
      state,
      4,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      false,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action closeAfterBackupFinish = all {
    state.scenario == CloseLiveBackup,
    state.stage == 4,
    not(state.backupHandleLive),
    state' = nextState(
      state,
      5,
      false,
      false,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupInitForCloseV2 = all {
    state.scenario == CloseV2LiveBackup,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      true,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action closeV2MarksZombieWithLiveBackup = all {
    state.scenario == CloseV2LiveBackup,
    state.stage == 1,
    state.backupHandleLive,
    state' = nextState(
      state,
      2,
      true,
      true,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupFinishAfterCloseV2 = all {
    state.scenario == CloseV2LiveBackup,
    state.stage == 2,
    state.backupHandleLive,
    state.connZombie,
    state' = nextState(
      state,
      3,
      false,
      false,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      false,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupInitForDonePath = all {
    state.scenario == BackupStepDoneFinish,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      true,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupStepDone = all {
    state.scenario == BackupStepDoneFinish,
    state.stage == 1,
    state.backupHandleLive,
    state' = nextState(
      state,
      2,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupFinishDonePath = all {
    state.scenario == BackupStepDoneFinish,
    state.stage == 2,
    state.backupHandleLive,
    state' = nextState(
      state,
      3,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      false,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupQueryMatches = all {
    state.scenario == BackupStepDoneFinish,
    state.stage == 3,
    not(state.backupHandleLive),
    state' = nextState(
      state,
      4,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      true,
      state.destReadTxnStarted
    ),
  }

  action backupInitForIncompletePath = all {
    state.scenario == BackupFinishIncomplete,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      true,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupStepPartial = all {
    state.scenario == BackupFinishIncomplete,
    state.stage == 1,
    state.backupHandleLive,
    state' = nextState(
      state,
      2,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupFinishIncompletePath = all {
    state.scenario == BackupFinishIncomplete,
    state.stage == 2,
    state.backupHandleLive,
    state' = nextState(
      state,
      3,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      false,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupInitForZeroStepPath = all {
    state.scenario == BackupStepZeroNoProgress,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      true,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupStepOneBeforeZero = all {
    state.scenario == BackupStepZeroNoProgress,
    state.stage == 1,
    state.backupHandleLive,
    state' = nextState(
      state,
      2,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupStepZeroNoProgress = all {
    state.scenario == BackupStepZeroNoProgress,
    state.stage == 2,
    state.backupHandleLive,
    state' = nextState(
      state,
      3,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupStepNegativeAfterZero = all {
    state.scenario == BackupStepZeroNoProgress,
    state.stage == 3,
    state.backupHandleLive,
    state' = nextState(
      state,
      4,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      false,
      true,
      state.destReadTxnStarted
    ),
  }

  action closeAfterZeroStepPath = all {
    state.scenario == BackupStepZeroNoProgress,
    state.stage == 4,
    not(state.backupHandleLive),
    state.backupQueryMatched,
    state' = nextState(
      state,
      5,
      false,
      false,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupInitForNegativeStepPath = all {
    state.scenario == BackupStepNegativeAllRemainingDone,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      true,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupStepNegativeAllRemaining = all {
    state.scenario == BackupStepNegativeAllRemainingDone,
    state.stage == 1,
    state.backupHandleLive,
    state' = nextState(
      state,
      2,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupFinishAfterNegativeStepPath = all {
    state.scenario == BackupStepNegativeAllRemainingDone,
    state.stage == 2,
    state.backupHandleLive,
    state' = nextState(
      state,
      3,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      false,
      true,
      state.destReadTxnStarted
    ),
  }

  action closeAfterNegativeStepPath = all {
    state.scenario == BackupStepNegativeAllRemainingDone,
    state.stage == 3,
    not(state.backupHandleLive),
    state.backupQueryMatched,
    state' = nextState(
      state,
      4,
      false,
      false,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupInitForTransientConflictPath = all {
    state.scenario == BackupStepTransientConflictRetry,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      true,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupStepConflictObserved = all {
    state.scenario == BackupStepTransientConflictRetry,
    state.stage == 1,
    state.backupHandleLive,
    state' = nextState(
      state,
      2,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      true,
      state.destReadTxnStarted
    ),
  }

  action backupStepRetryAfterConflict = all {
    state.scenario == BackupStepTransientConflictRetry,
    state.stage == 2,
    state.backupHandleLive,
    state.backupQueryMatched,
    state' = nextState(
      state,
      3,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupFinishAfterTransientConflictPath = all {
    state.scenario == BackupStepTransientConflictRetry,
    state.stage == 3,
    state.backupHandleLive,
    state.backupQueryMatched,
    state' = nextState(
      state,
      4,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      false,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action closeAfterTransientConflictPath = all {
    state.scenario == BackupStepTransientConflictRetry,
    state.stage == 4,
    not(state.backupHandleLive),
    state.backupQueryMatched,
    state' = nextState(
      state,
      5,
      false,
      false,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      state.backupHandleLive,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action backupInitSameConnectionError = all {
    state.scenario == BackupInitSameConnectionError,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      false,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action startDestReadTxn = all {
    state.scenario == BackupInitDestReadTxnError,
    state.stage == 0,
    state' = nextState(
      state,
      1,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      false,
      state.backupQueryMatched,
      true
    ),
  }

  action backupInitDestTxnError = all {
    state.scenario == BackupInitDestReadTxnError,
    state.stage == 1,
    state.destReadTxnStarted,
    state' = nextState(
      state,
      2,
      state.connOpen,
      state.connZombie,
      state.closeNullCalled,
      state.closeV2NullCalled,
      state.prepareCaseSelected,
      state.prepareComparedEqual,
      state.stmtHandleLive,
      false,
      state.backupQueryMatched,
      state.destReadTxnStarted
    ),
  }

  action stutter = state' = state

  action step = any {
    finalizeNullNoOp,
    closeNullNoOp,
    closeV2NullNoOp,
    prepareStmtForClose,
    closeBusyWithLiveStmt,
    stepStmtAfterCloseBusy,
    finalizeStmtAfterCloseBusy,
    closeAfterFinalize,
    prepareStmtForCloseV2,
    closeV2MarksZombieWithLiveStmt,
    stepStmtAfterCloseV2,
    finalizeStmtAfterCloseV2,
    selectPrepareCase,
    comparePrepareZeroFlags,
    closeAfterPrepareComparison,
    backupInitForClose,
    closeBusyWithLiveBackup,
    backupStepDoneAfterCloseBusy,
    backupFinishAfterCloseBusy,
    closeAfterBackupFinish,
    backupInitForCloseV2,
    closeV2MarksZombieWithLiveBackup,
    backupFinishAfterCloseV2,
    backupInitForDonePath,
    backupStepDone,
    backupFinishDonePath,
    backupQueryMatches,
    backupInitForIncompletePath,
    backupStepPartial,
    backupFinishIncompletePath,
    backupInitForZeroStepPath,
    backupStepOneBeforeZero,
    backupStepZeroNoProgress,
    backupStepNegativeAfterZero,
    closeAfterZeroStepPath,
    backupInitForNegativeStepPath,
    backupStepNegativeAllRemaining,
    backupFinishAfterNegativeStepPath,
    closeAfterNegativeStepPath,
    backupInitForTransientConflictPath,
    backupStepConflictObserved,
    backupStepRetryAfterConflict,
    backupFinishAfterTransientConflictPath,
    closeAfterTransientConflictPath,
    backupInitSameConnectionError,
    startDestReadTxn,
    backupInitDestTxnError,
    stutter,
  }

  val lifecycleFinalizeNullNoOp =
    (state.scenario == FinalizeNull and state.stage == 1) implies (
      not(state.connOpen)
      and not(state.connZombie)
      and not(state.stmtHandleLive)
      and not(state.backupHandleLive)
    )

  val lifecycleCloseNullNoOp =
    (state.scenario == CloseNull and (state.closeNullCalled or state.closeV2NullCalled)) implies (
      not(state.connOpen)
      and not(state.connZombie)
      and not(state.stmtHandleLive)
      and not(state.backupHandleLive)
    )

  val lifecycleCloseLiveStmtPath =
    (state.scenario == CloseLiveStmt) implies (
      ((state.stage <= 4) implies state.connOpen)
      and ((state.stage >= 1 and state.stage <= 3) implies state.stmtHandleLive)
      and ((state.stage >= 4) implies not(state.stmtHandleLive))
      and ((state.stage == 5) implies not(state.connOpen))
      and not(state.connZombie)
    )

  val lifecycleCloseV2LiveStmtPath =
    (state.scenario == CloseV2LiveStmt) implies (
      ((state.stage <= 1) implies (state.connOpen and not(state.connZombie)))
      and ((state.stage >= 2 and state.stage <= 3) implies (
        state.connOpen and state.connZombie and state.stmtHandleLive
      ))
      and ((state.stage == 4) implies (
        not(state.connOpen) and not(state.connZombie) and not(state.stmtHandleLive)
      ))
    )

  val lifecyclePrepareV2V3ZeroFlagsEquivalent =
    (state.scenario == PrepareV2V3ZeroFlags) implies (
      ((state.stage == 0) implies (state.connOpen and not(state.prepareCaseSelected)))
      and ((state.stage >= 1) implies state.prepareCaseSelected)
      and ((state.stage >= 2) implies state.prepareComparedEqual)
      and ((state.stage == 3) implies not(state.connOpen))
    )

  val lifecycleCloseLiveBackupPath =
    (state.scenario == CloseLiveBackup) implies (
      ((state.stage <= 4) implies state.connOpen)
      and ((state.stage >= 1 and state.stage <= 3) implies state.backupHandleLive)
      and ((state.stage >= 4) implies not(state.backupHandleLive))
      and ((state.stage == 5) implies not(state.connOpen))
      and not(state.connZombie)
    )

  val lifecycleCloseV2LiveBackupPath =
    (state.scenario == CloseV2LiveBackup) implies (
      ((state.stage <= 1) implies (state.connOpen and not(state.connZombie)))
      and ((state.stage == 2) implies (
        state.connOpen and state.connZombie and state.backupHandleLive
      ))
      and ((state.stage == 3) implies (
        not(state.connOpen) and not(state.connZombie) and not(state.backupHandleLive)
      ))
    )

  val lifecycleBackupStepDoneFinishPath =
    (state.scenario == BackupStepDoneFinish) implies (
      state.connOpen
      and ((state.stage >= 1 and state.stage <= 2) implies state.backupHandleLive)
      and ((state.stage >= 3) implies not(state.backupHandleLive))
      and ((state.stage == 4) implies state.backupQueryMatched)
    )

  val lifecycleBackupFinishIncompletePath =
    (state.scenario == BackupFinishIncomplete) implies (
      state.connOpen
      and ((state.stage >= 1 and state.stage <= 2) implies state.backupHandleLive)
      and ((state.stage == 3) implies (
        not(state.backupHandleLive) and not(state.backupQueryMatched)
      ))
    )

  val lifecycleBackupStepZeroNoProgressPath =
    (state.scenario == BackupStepZeroNoProgress) implies (
      ((state.stage <= 4) implies state.connOpen)
      and ((state.stage >= 1 and state.stage <= 3) implies state.backupHandleLive)
      and ((state.stage >= 4) implies state.backupQueryMatched)
      and ((state.stage >= 4) implies not(state.backupHandleLive))
      and ((state.stage == 5) implies not(state.connOpen))
    )

  val lifecycleBackupStepNegativeAllRemainingPath =
    (state.scenario == BackupStepNegativeAllRemainingDone) implies (
      ((state.stage <= 3) implies state.connOpen)
      and ((state.stage >= 1 and state.stage <= 2) implies state.backupHandleLive)
      and ((state.stage >= 3) implies (
        not(state.backupHandleLive) and state.backupQueryMatched
      ))
      and ((state.stage == 4) implies not(state.connOpen))
    )

  val lifecycleBackupStepTransientConflictPath =
    (state.scenario == BackupStepTransientConflictRetry) implies (
      ((state.stage <= 4) implies state.connOpen)
      and ((state.stage >= 1 and state.stage <= 3) implies state.backupHandleLive)
      and ((state.stage >= 2) implies state.backupQueryMatched)
      and ((state.stage >= 4) implies not(state.backupHandleLive))
      and ((state.stage == 5) implies not(state.connOpen))
    )

  val lifecycleBackupInitSameConnectionErrorPath =
    (state.scenario == BackupInitSameConnectionError and state.stage == 1) implies (
      state.connOpen
      and not(state.connZombie)
      and not(state.backupHandleLive)
    )

  val lifecycleBackupInitDestReadTxnErrorPath =
    (state.scenario == BackupInitDestReadTxnError) implies (
      ((state.stage == 0) implies (
        state.connOpen and not(state.destReadTxnStarted) and not(state.backupHandleLive)
      ))
      and ((state.stage == 1) implies (
        state.connOpen and state.destReadTxnStarted and not(state.backupHandleLive)
      ))
      and ((state.stage == 2) implies (
        state.connOpen and state.destReadTxnStarted and not(state.backupHandleLive)
      ))
    )
}
