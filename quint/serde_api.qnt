module SqliteSerdeApi {
  type Scenario = str
  type ReturnCode = str

  val ReadTxnBusy: Scenario = "deserialize_read_txn_busy"
  val BackupBusy: Scenario = "deserialize_backup_busy"
  val NullSchemaMain: Scenario = "deserialize_null_schema_main"
  val AttachedSchema: Scenario = "deserialize_attached_schema"
  val TempSchemaError: Scenario = "deserialize_temp_schema_error"
  val MissingSchemaError: Scenario = "deserialize_missing_schema_error"
  val WalImageCantopen: Scenario = "deserialize_wal_image_cantopen"
  val ReadonlyReadWrite: Scenario = "deserialize_readonly_read_write"
  val ResizeableGrowth: Scenario = "deserialize_resizeable_growth"
  val NonresizeableGrowth: Scenario = "deserialize_nonresizeable_growth"
  val FreeOnCloseFailure: Scenario = "deserialize_freeonclose_failure"
  val NegativeSizeArmor: Scenario = "deserialize_negative_size_armor"

  val SQLITE_OK: ReturnCode = "SQLITE_OK"
  val SQLITE_BUSY: ReturnCode = "SQLITE_BUSY"
  val SQLITE_ERROR: ReturnCode = "SQLITE_ERROR"
  val SQLITE_FULL: ReturnCode = "SQLITE_FULL"
  val SQLITE_READONLY: ReturnCode = "SQLITE_READONLY"
  val SQLITE_CANTOPEN: ReturnCode = "SQLITE_CANTOPEN"
  val SQLITE_MISUSE: ReturnCode = "SQLITE_MISUSE"
  val NO_CALL: ReturnCode = "NO_CALL"

  type ModelState = {
    scenario: Scenario,
    readTxn: bool,
    backupSource: bool,
    deserialized: bool,
    readonlyRead: bool,
    readonlyWriteRejected: bool,
    resizeableGrew: bool,
    grewWithinLimit: bool,
    rejectedBeyondLimit: bool,
    walImageUseFailed: bool,
    freeOnCloseFreed: bool,
    rc: ReturnCode,
    divergence: bool,
  }

  var state: ModelState

  val Scenarios: Set[Scenario] = Set(
    ReadTxnBusy,
    BackupBusy,
    NullSchemaMain,
    AttachedSchema,
    TempSchemaError,
    MissingSchemaError,
    WalImageCantopen,
    ReadonlyReadWrite,
    ResizeableGrowth,
    NonresizeableGrowth,
    FreeOnCloseFailure,
    NegativeSizeArmor
  )

  def fresh(scenario: Scenario): ModelState = {
    scenario: scenario,
    readTxn: false,
    backupSource: false,
    deserialized: false,
    readonlyRead: false,
    readonlyWriteRejected: false,
    resizeableGrew: false,
    grewWithinLimit: false,
    rejectedBeyondLimit: false,
    walImageUseFailed: false,
    freeOnCloseFreed: false,
    rc: NO_CALL,
    divergence: false,
  }

  def copyWithRc(
    current: ModelState,
    rc: ReturnCode,
    deserialized: bool,
    readonlyRead: bool,
    readonlyWriteRejected: bool,
    resizeableGrew: bool,
    grewWithinLimit: bool,
    rejectedBeyondLimit: bool,
    walImageUseFailed: bool,
    freeOnCloseFreed: bool,
    divergence: bool
  ): ModelState = {
    scenario: current.scenario,
    readTxn: current.readTxn,
    backupSource: current.backupSource,
    deserialized: deserialized,
    readonlyRead: readonlyRead,
    readonlyWriteRejected: readonlyWriteRejected,
    resizeableGrew: resizeableGrew,
    grewWithinLimit: grewWithinLimit,
    rejectedBeyondLimit: rejectedBeyondLimit,
    walImageUseFailed: walImageUseFailed,
    freeOnCloseFreed: freeOnCloseFreed,
    rc: rc,
    divergence: divergence,
  }

  def withResult(
    current: ModelState,
    rc: ReturnCode,
    deserialized: bool,
    freeOnCloseFreed: bool
  ): ModelState =
    copyWithRc(
      current,
      rc,
      deserialized,
      current.readonlyRead,
      current.readonlyWriteRejected,
      current.resizeableGrew,
      current.grewWithinLimit,
      current.rejectedBeyondLimit,
      current.walImageUseFailed,
      freeOnCloseFreed,
      false
    )

  def expectedDocRc(current: ModelState): ReturnCode =
    if (current.scenario == ReadTxnBusy and current.readTxn) {
      SQLITE_BUSY
    } else if (current.scenario == BackupBusy and current.backupSource) {
      SQLITE_BUSY
    } else if (current.scenario == TempSchemaError) {
      SQLITE_ERROR
    } else if (current.scenario == MissingSchemaError) {
      SQLITE_ERROR
    } else if (current.scenario == FreeOnCloseFailure) {
      SQLITE_ERROR
    } else if (current.scenario == NegativeSizeArmor) {
      SQLITE_MISUSE
    } else {
      SQLITE_OK
    }

  action initDoc = {
    nondet scenario = Scenarios.oneOf()
    state' = fresh(scenario)
  }

  action init = initDoc

  action startReadTxn = all {
    state.scenario == ReadTxnBusy,
    not(state.readTxn),
    not(state.deserialized),
    state' = {
      scenario: state.scenario,
      readTxn: true,
      backupSource: state.backupSource,
      deserialized: state.deserialized,
      readonlyRead: state.readonlyRead,
      readonlyWriteRejected: state.readonlyWriteRejected,
      resizeableGrew: state.resizeableGrew,
      grewWithinLimit: state.grewWithinLimit,
      rejectedBeyondLimit: state.rejectedBeyondLimit,
      walImageUseFailed: state.walImageUseFailed,
      freeOnCloseFreed: state.freeOnCloseFreed,
      rc: state.rc,
      divergence: state.divergence,
    },
  }

  action startBackupSource = all {
    state.scenario == BackupBusy,
    not(state.backupSource),
    not(state.deserialized),
    state' = {
      scenario: state.scenario,
      readTxn: state.readTxn,
      backupSource: true,
      deserialized: state.deserialized,
      readonlyRead: state.readonlyRead,
      readonlyWriteRejected: state.readonlyWriteRejected,
      resizeableGrew: state.resizeableGrew,
      grewWithinLimit: state.grewWithinLimit,
      rejectedBeyondLimit: state.rejectedBeyondLimit,
      walImageUseFailed: state.walImageUseFailed,
      freeOnCloseFreed: state.freeOnCloseFreed,
      rc: state.rc,
      divergence: state.divergence,
    },
  }

  action deserialize = all {
    state.rc == NO_CALL,
    state' = withResult(
      state,
      expectedDocRc(state),
      expectedDocRc(state) == SQLITE_OK,
      state.scenario == FreeOnCloseFailure
    ),
  }

  action readonlyRead = all {
    state.scenario == ReadonlyReadWrite,
    state.deserialized,
    not(state.readonlyRead),
    state' = copyWithRc(
      state,
      SQLITE_OK,
      state.deserialized,
      true,
      state.readonlyWriteRejected,
      state.resizeableGrew,
      state.grewWithinLimit,
      state.rejectedBeyondLimit,
      state.walImageUseFailed,
      state.freeOnCloseFreed,
      state.divergence
    ),
  }

  action readonlyWriteReject = all {
    state.scenario == ReadonlyReadWrite,
    state.deserialized,
    state.readonlyRead,
    not(state.readonlyWriteRejected),
    state' = copyWithRc(
      state,
      SQLITE_READONLY,
      state.deserialized,
      state.readonlyRead,
      true,
      state.resizeableGrew,
      state.grewWithinLimit,
      state.rejectedBeyondLimit,
      state.walImageUseFailed,
      state.freeOnCloseFreed,
      state.divergence
    ),
  }

  action resizeableGrow = all {
    state.scenario == ResizeableGrowth,
    state.deserialized,
    not(state.resizeableGrew),
    state' = copyWithRc(
      state,
      SQLITE_OK,
      state.deserialized,
      state.readonlyRead,
      state.readonlyWriteRejected,
      true,
      state.grewWithinLimit,
      state.rejectedBeyondLimit,
      state.walImageUseFailed,
      state.freeOnCloseFreed,
      state.divergence
    ),
  }

  action useWalImage = all {
    state.scenario == WalImageCantopen,
    state.deserialized,
    not(state.walImageUseFailed),
    state' = copyWithRc(
      state,
      SQLITE_CANTOPEN,
      state.deserialized,
      state.readonlyRead,
      state.readonlyWriteRejected,
      state.resizeableGrew,
      state.grewWithinLimit,
      state.rejectedBeyondLimit,
      true,
      state.freeOnCloseFreed,
      state.divergence
    ),
  }

  action growWithinLimit = all {
    state.scenario == NonresizeableGrowth,
    state.deserialized,
    not(state.grewWithinLimit),
    state' = copyWithRc(
      state,
      SQLITE_OK,
      state.deserialized,
      state.readonlyRead,
      state.readonlyWriteRejected,
      state.resizeableGrew,
      true,
      state.rejectedBeyondLimit,
      state.walImageUseFailed,
      state.freeOnCloseFreed,
      state.divergence
    ),
  }

  action rejectBeyondLimit = all {
    state.scenario == NonresizeableGrowth,
    state.grewWithinLimit,
    not(state.rejectedBeyondLimit),
    state' = copyWithRc(
      state,
      SQLITE_FULL,
      state.deserialized,
      state.readonlyRead,
      state.readonlyWriteRejected,
      state.resizeableGrew,
      state.grewWithinLimit,
      true,
      state.walImageUseFailed,
      state.freeOnCloseFreed,
      state.divergence
    ),
  }

  action stutter = state' = state

  action step = any {
    startReadTxn,
    startBackupSource,
    deserialize,
    readonlyRead,
    readonlyWriteReject,
    resizeableGrow,
    useWalImage,
    growWithinLimit,
    rejectBeyondLimit,
    stutter,
  }

  val noDocDivergence =
    not(state.divergence)

  val docBusyConflictsReturnBusy =
    (
      state.rc != NO_CALL
      and (
        (state.scenario == ReadTxnBusy and state.readTxn)
        or (state.scenario == BackupBusy and state.backupSource)
      )
    ) implies state.rc == SQLITE_BUSY

  val docBusyConflictsDoNotInstall =
    (
      state.rc == SQLITE_BUSY
      and (
        (state.scenario == ReadTxnBusy and state.readTxn)
        or (state.scenario == BackupBusy and state.backupSource)
      )
    ) implies not(state.deserialized)

  val successfulDeserializeInstalls =
    (
      state.scenario == NullSchemaMain
      or state.scenario == AttachedSchema
    ) and state.rc != NO_CALL implies (
      state.rc == SQLITE_OK and state.deserialized
    )

  val schemaErrorsDoNotInstall =
    (
      (state.scenario == TempSchemaError or state.scenario == MissingSchemaError)
      and state.rc != NO_CALL
    ) implies (
      state.rc == SQLITE_ERROR and not(state.deserialized)
    )

  val apiArmorNegativeSizesReturnMisuse =
    (
      state.scenario == NegativeSizeArmor
      and state.rc != NO_CALL
    ) implies (
      state.rc == SQLITE_MISUSE and not(state.deserialized)
    )

  val readonlyWriteRequiresReadonlyDeserialize =
    state.readonlyWriteRejected implies (
      state.scenario == ReadonlyReadWrite
      and state.deserialized
      and state.readonlyRead
      and state.rc == SQLITE_READONLY
    )

  val resizeableGrowthRequiresResizeableDeserialize =
    state.resizeableGrew implies (
      state.scenario == ResizeableGrowth
      and state.deserialized
      and state.rc == SQLITE_OK
    )

  val walImageUseFailsCantopen =
    state.walImageUseFailed implies (
      state.scenario == WalImageCantopen
      and state.deserialized
      and state.rc == SQLITE_CANTOPEN
    )

  val docFreeOnCloseFailureReturnsError =
    (
      state.scenario == FreeOnCloseFailure
      and state.rc != NO_CALL
    ) implies (
      state.rc == SQLITE_ERROR
      and state.freeOnCloseFreed
      and not(state.deserialized)
    )

  val noSuccessfulDeserializeAfterFreeOnCloseFailure =
    state.freeOnCloseFreed implies (
      state.scenario == FreeOnCloseFailure
      and state.rc == SQLITE_ERROR
      and not(state.deserialized)
    )

  val nonresizeableRejectionRequiresBoundedGrowth =
    state.rejectedBeyondLimit implies (
      state.scenario == NonresizeableGrowth
      and state.grewWithinLimit
      and state.rc == SQLITE_FULL
    )
}
