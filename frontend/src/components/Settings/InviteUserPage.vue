<template>
  <div class="flex h-full flex-col gap-6 py-8 px-6 text-ink-gray-8">
    <div class="flex px-2 justify-between">
      <div class="flex flex-col gap-1 w-9/12">
        <h2 class="flex gap-2 text-2xl-semibold leading-none h-5">
          {{ __('Send Invites To') }}
        </h2>
        <p class="text-p-base text-ink-gray-6">
          {{
            __(
              'Invite users to access CRM. Specify their roles to control access and permissions',
            )
          }}
        </p>
      </div>
      <div class="flex item-center space-x-2 w-3/12 justify-end">
        <Button
          :label="__('Send Invite')"
          variant="solid"
          :disabled="isSendDisabled"
          :loading="inviteByEmail.loading"
          @click="inviteByEmail.submit()"
        />
      </div>
    </div>
    <div class="flex-1 flex flex-col px-2 gap-8 overflow-y-auto">
      <div>
        <div class="grid grid-cols-2 gap-4">
          <FormControl
            v-model="firstName"
            type="text"
            :label="__('First Name')"
            :disabled="inviteByEmail.loading"
          />
          <FormControl
            v-model="lastName"
            type="text"
            :label="__('Last Name')"
            :disabled="inviteByEmail.loading"
          />
        </div>
        <FormControl
          v-model="mobileNo"
          type="text"
          class="mt-4"
          :label="__('Telefon')"
          placeholder="+48 000 000 000"
          :disabled="inviteByEmail.loading"
        />
        <FormControl
          v-model="email"
          type="email"
          class="mt-4"
          :label="__('Invite By Email')"
          placeholder="user@example.com"
          :disabled="inviteByEmail.loading"
        />
        <div
          v-if="userExistMessage || inviteeExistMessage"
          class="text-xs text-ink-red-6 mt-1.5"
        >
          {{ userExistMessage || inviteeExistMessage }}
        </div>
        <FormControl
          v-model="role"
          type="select"
          class="mt-4"
          :label="__('Invite As')"
          :options="roleOptions"
          :description="description"
        />
        <FormControl
          v-model="volteoRole"
          type="select"
          class="mt-4"
          :label="__('Volteo role')"
          :options="volteoRoleOptions"
        />
        <FormControl
          v-if="volteoRole"
          v-model="hierarchyParent"
          type="select"
          class="mt-4"
          :label="__('Reports to (hierarchy)')"
          :options="hierarchyOptions"
        />
        <div class="flex flex-col gap-2 mt-4">
          <FormControl
            type="checkbox"
            :label="__('Linia OZE')"
            :modelValue="linieOze"
            :disabled="inviteByEmail.loading"
            @update:modelValue="(val) => (linieOze = Boolean(val))"
          />
          <FormControl
            type="checkbox"
            :label="__('Linia Czyste Powietrze')"
            :modelValue="linieCp"
            :disabled="inviteByEmail.loading"
            @update:modelValue="(val) => (linieCp = Boolean(val))"
          />
          <div v-if="!linieOze && !linieCp" class="text-xs text-ink-red-6">
            {{ __('Wybierz co najmniej jedną linię produktową') }}
          </div>
          <FormControl
            type="checkbox"
            :label="__('Leady')"
            :modelValue="linieLeady"
            :disabled="inviteByEmail.loading"
            @update:modelValue="(val) => (linieLeady = Boolean(val))"
          />
        </div>
      </div>
      <template v-if="pendingInvitations.data?.length">
        <div class="flex flex-col gap-4">
          <div class="flex items-center justify-between text-base-semibold">
            <div>{{ __('Pending Invites') }}</div>
          </div>
          <ul class="flex flex-col gap-1">
            <li
              v-for="user in pendingInvitations.data"
              :key="user.name"
              class="flex items-center justify-between px-2 py-1 rounded-lg bg-surface-gray-2"
            >
              <div class="text-base">
                <span class="text-ink-gray-8">
                  {{ user.email }}
                  <template v-if="user.first_name || user.last_name">
                    ({{
                      [user.first_name, user.last_name]
                        .filter(Boolean)
                        .join(' ')
                    }})
                  </template>
                  <template v-if="user.mobile_no">
                    · {{ user.mobile_no }}
                  </template>
                </span>
                <span class="text-ink-gray-5">
                  ({{ roleMap[user.role]
                  }}<template v-if="user.volteo_role">
                    · {{ volteoRoleMap[user.volteo_role] }}</template
                  >
                  · {{ linieLabel(user) }})
                </span>
              </div>
              <div>
                <Button
                  :tooltip="__('Delete Invitation')"
                  icon="lucide-x"
                  variant="ghost"
                  :loading="
                    pendingInvitations.delete.loading &&
                    pendingInvitations.delete.params.name === user.name
                  "
                  @click="pendingInvitations.delete.submit(user.name)"
                />
              </div>
            </li>
          </ul>
        </div>
      </template>
    </div>
    <ErrorMessage :message="error" />
  </div>
</template>
<script setup>
import { validateEmail } from '@/utils'
import { usersStore } from '@/stores/users'
import { useOnboarding, useTelemetry } from 'frappe-ui/frappe'
import {
  toast,
  createListResource,
  createResource,
  FormControl,
} from 'frappe-ui'
import { ref, computed } from 'vue'

const { updateOnboardingStep } = useOnboarding('frappecrm')
const { users, isAdmin, isVolteoAdmin } = usersStore()
const { capture } = useTelemetry()

// Single-person invite form (issue #14): the inviter — not the invitee —
// types the invitee's name here, because the invitee never gets a chance
// to supply it before the NDA gate on first login compares the typed name
// against User.full_name (crm.api.oswiadczenie._pelne_imie_i_nazwisko).
const firstName = ref('')
const lastName = ref('')
const mobileNo = ref('')
const email = ref('')
const role = ref('Sales User')
const volteoRole = ref('Volteo D2D Sales')
const hierarchyParent = ref('')
// Product-line selection (issue #17): both checked by default, mirroring
// the pre-#17 behaviour of unrestricted access — see
// ops/crm-invitation-linie-telefon.py "Why".
const linieOze = ref(true)
const linieCp = ref(true)
// Leady module access (issue #27): UNchecked by default — unlike
// linieOze/linieCp above, there is no pre-existing "everyone already had
// this" behaviour to preserve. Matches the safe-rollout default recommended
// for issue #27 (ops/crm-linia-leady.py: BACKFILL_DOMYSLNA=0, CRM
// Invitation.linia_leady schema default "0"). Independent of the product
// lines — not part of the "select at least one" requirement below.
const linieLeady = ref(false)
const error = ref(null)

const isValidEmail = computed(() => validateEmail(email.value.trim()))

const userExistMessage = computed(() => {
  const trimmed = email.value.trim()
  if (!isValidEmail.value) return null
  if (!users.data?.crmUsers?.length) return null

  const exists = users.data.crmUsers.some((user) => user.name === trimmed)
  if (!exists) return null

  return __('User with email {0} already exists', [trimmed])
})

const inviteeExistMessage = computed(() => {
  const trimmed = email.value.trim()
  if (!isValidEmail.value) return null
  if (!pendingInvitations.data?.length) return null

  const exists = pendingInvitations.data.some((user) => user.email === trimmed)
  if (!exists) return null

  return __('User with email {0} already invited', [trimmed])
})

const description = computed(() => {
  return {
    'System Manager':
      'Can manage all aspects of the CRM, including user management, customizations and settings.',
    'Sales Manager':
      'Can manage and invite new users, and create public & private views (reports).',
    'Sales User':
      'Can work with leads and deals and create private views (reports).',
  }[role.value]
})

const roleOptions = computed(() => {
  return [
    { value: 'Sales User', label: __('Sales User') },
    ...(isAdmin() ? [{ value: 'Sales Manager', label: __('Manager') }] : []),
    ...(isAdmin() ? [{ value: 'System Manager', label: __('Admin') }] : []),
  ]
})

const roleMap = {
  'Sales User': __('Sales User'),
  'Sales Manager': __('Manager'),
  'System Manager': __('Admin'),
}

// Volteo-specific role assigned alongside the stock role above. Backoffice
// is only offered to Volteo admins — same gate the backend enforces in
// `crm.api.invite_by_email`.
const volteoRoleOptions = computed(() => {
  return [
    { value: '', label: __('None') },
    { value: 'Volteo D2D Sales', label: __('D2D Sales Rep') },
    ...(isVolteoAdmin()
      ? [{ value: 'Volteo Backend', label: __('Backoffice') }]
      : []),
  ]
})

const volteoRoleMap = {
  'Volteo D2D Sales': __('D2D Sales Rep'),
  'Volteo Backend': __('Backoffice'),
}

// Sales User has stock read on CRM Sales Hierarchy, so this list resource
// resolves for every inviter, not just admins.
const hierarchyList = createListResource({
  type: 'list',
  doctype: 'CRM Sales Hierarchy',
  fields: ['name', 'full_name', 'is_group'],
  pageLength: 999,
  auto: true,
})

const hierarchyOptions = computed(() => {
  return [
    { value: '', label: __('Directly under management (tree root)') },
    ...(hierarchyList.data || []).map((node) => ({
      value: node.name,
      label: node.full_name || node.name,
    })),
  ]
})

const isSendDisabled = computed(() => {
  return (
    !isValidEmail.value ||
    !firstName.value.trim() ||
    !lastName.value.trim() ||
    Boolean(userExistMessage.value) ||
    Boolean(inviteeExistMessage.value) ||
    (!linieOze.value && !linieCp.value)
  )
})

const inviteByEmail = createResource({
  url: 'crm.api.invite_by_email',
  makeParams() {
    return {
      emails: email.value.trim(),
      role: role.value,
      volteo_role: volteoRole.value || '',
      hierarchy_parent: hierarchyParent.value || '',
      first_name: firstName.value.trim(),
      last_name: lastName.value.trim(),
      mobile_no: mobileNo.value.trim(),
      linia_oze: linieOze.value ? 1 : 0,
      linia_cp: linieCp.value ? 1 : 0,
      linia_leady: linieLeady.value ? 1 : 0,
    }
  },
  onSuccess() {
    role.value = 'Sales User'
    volteoRole.value = 'Volteo D2D Sales'
    hierarchyParent.value = ''
    error.value = null
    firstName.value = ''
    lastName.value = ''
    mobileNo.value = ''
    email.value = ''
    linieOze.value = true
    linieCp.value = true
    linieLeady.value = false
    pendingInvitations.reload()
    toast.success(__('Invitations sent successfully'))
    updateOnboardingStep('invite_your_team')
    capture('user_invited')
  },
  onError(err) {
    error.value = err?.messages?.[0]
    toast.error(error.value)
  },
})

const pendingInvitations = createListResource({
  type: 'list',
  doctype: 'CRM Invitation',
  filters: { status: 'Pending' },
  fields: [
    'name',
    'email',
    'role',
    'volteo_role',
    'first_name',
    'last_name',
    'mobile_no',
    'linia_oze',
    'linia_cp',
    'linia_leady',
  ],
  pageLength: 999,
  auto: true,
})

// Rows created before ops/crm-invitation-linie-telefon.py ran carry
// undefined/None for linia_oze/linia_cp — render those as the legacy
// default ("OZE + CP"), matching the pre-#17 behaviour of unrestricted
// product-line access (same resolution as
// CRMInvitation._resolve_linia_flag on the backend, default=1 for these
// two). linia_leady (issue #27) resolves the OPPOSITE way for
// undefined/missing — rendered as OFF, mirroring the backend's
// `_resolve_linia_flag("linia_leady", default=0)` — since there is no
// pre-existing "everyone already had it" behaviour for a module that never
// had per-user access control before.
function linieLabel(user) {
  const oze = user.linia_oze === 0 || user.linia_oze === '0' ? false : true
  const cp = user.linia_cp === 0 || user.linia_cp === '0' ? false : true
  const leady = user.linia_leady === 1 || user.linia_leady === '1' ? true : false
  const parts = []
  if (oze) parts.push(__('OZE'))
  if (cp) parts.push(__('CP'))
  if (leady) parts.push(__('Leady'))
  return parts.length ? parts.join(' + ') : __('brak linii')
}
</script>
