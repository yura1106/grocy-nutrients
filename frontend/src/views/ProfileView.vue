<template>
  <div class="bg-gray-100">
    <div class="py-10">
      <PageHeader />
      <main>
        <div class="max-w-7xl mx-auto sm:px-6 lg:px-8">
          <div class="px-4 py-8 sm:px-0">
            <ProfileInformation />
            <HealthParameters />
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
import HealthParameters from '../components/profile/HealthParameters.vue'
import HouseholdsSection from '../components/profile/HouseholdsSection.vue'
import DangerZone from '../components/profile/DangerZone.vue'
import PageHeader from '../components/PageHeader.vue'
</script>
