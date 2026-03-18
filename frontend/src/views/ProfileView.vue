<template>
  <div class="bg-gray-100">
    <div class="py-10">
      <header>
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 class="text-3xl font-bold leading-tight text-gray-900">Profile</h1>
        </div>
      </header>
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <ProfileInformation />
            <HouseholdsSection />
            <DangerZone />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import ProfileInformation from '../components/profile/ProfileInformation.vue'
import HouseholdsSection from '../components/profile/HouseholdsSection.vue'
import DangerZone from '../components/profile/DangerZone.vue'
</script>
